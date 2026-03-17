#!/usr/bin/env python3
import subprocess
import time
import pathlib
import sys
import os
import signal

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK   = "/opt/homebrew/bin/cliclick"
CONVERT    = "/opt/homebrew/bin/convert"

clicker_proc = None

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def start_allow_clicker():
    global clicker_proc
    script = '''
    repeat
        tell application "System Events"
            repeat with p in (every process)
                try
                    repeat with w in (every window of p)
                        try
                            if exists button "Allow" of w then
                                click button "Allow" of w
                                delay 0.4
                            end if
                        end try
                    end repeat
                end try
            end repeat
        end tell
        delay 0.5
    end repeat
    '''
    clicker_proc = subprocess.Popen(['osascript', '-e', script],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
    log("Background Allow clicker started")

def stop_allow_clicker():
    if clicker_proc:
        clicker_proc.terminate()
        try:
            clicker_proc.wait(timeout=3)
        except:
            pass
        log("Background Allow clicker stopped")

def shot(name):
    path = DEBUG / name
    subprocess.run(["/usr/sbin/screencapture", "-x", str(path)], check=False)
    log(f"Screenshot: {name}")

def applescript(script_str):
    result = subprocess.run(['osascript', '-e', script_str],
                            capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

def cliclick(x, y):
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=True, timeout=6)
        log(f"cliclick → ({x}, {y})")
    except Exception as e:
        log(f"cliclick failed: {e}")
        applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def activate_rustdesk():
    log("Activating RustDesk window")
    applescript('tell application "RustDesk" to activate')
    time.sleep(2.5)

def get_button_position(app_name, button_text):
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontmost to true
            delay 0.4
            try
                set btn to first button of window 1 whose title contains "{button_text}"
                set pos to position of btn
                set sz to size of btn
                set cx to (item 1 of pos) + (item 1 of sz div 2)
                set cy to (item 2 of pos) + (item 2 of sz div 2)
                return cx & "," & cy
            on error
                return "not-found"
            end try
        end tell
    end tell
    '''
    ok, out, err = applescript(script)
    if ok and out != "not-found" and "," in out:
        try:
            x, y = map(int, out.split(","))
            log(f"Found '{button_text}' at ({x},{y})")
            return (x, y)
        except:
            pass
    log(f"No '{button_text}' button found via AppleScript")
    return None

def preprocess_ocr(img_path):
    pre = img_path.with_name(img_path.stem + "_pre.png")
    cmd = [
        CONVERT, str(img_path),
        "-colorspace", "Gray",
        "-normalize",
        "-contrast-stretch", "2%",
        "-sharpen", "0x1.2",
        "-threshold", "60%",
        str(pre)
    ]
    subprocess.run(cmd, check=False, timeout=12)
    return pre if pre.exists() else img_path

def find_text_by_ocr(target_text):
    shot("ocr_search.png")
    tmp = DEBUG / "ocr_tmp.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp)], check=False)
    pre_img = preprocess_ocr(tmp)
    base = pre_img.with_suffix('')
    cmd = [TESSERACT, str(pre_img), str(base), "--psm", "7", "tsv"]
    subprocess.run(cmd, check=False, timeout=15, capture_output=True)
    tsv = base.with_suffix('.tsv')
    if not tsv.exists():
        log("No TSV produced by tesseract")
        for p in [tmp, pre_img]:
            p.unlink(missing_ok=True)
        return None

    with open(tsv, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for p in [tsv, tmp, pre_img]:
        p.unlink(missing_ok=True)

    target_lower = target_text.lower()
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < 12:
            continue
        conf = parts[10]
        text = parts[11].strip().lower()
        if conf.isdigit() and int(conf) > 28 and target_lower in text:
            try:
                x = int(parts[6]) + int(parts[8]) // 2
                y = int(parts[7]) + int(parts[9]) // 2
                log(f"OCR found '{target_text}' ≈ '{text}' at ({x},{y}) conf={conf}")
                return (x, y)
            except:
                pass
    log(f"OCR did not find '{target_text}'")
    return None

def click_configure():
    log("Trying to click Configure in RustDesk")
    activate_rustdesk()
    time.sleep(1.5)

    methods = [
        ("AppleScript 'Configure'", lambda: get_button_position("RustDesk", "Configure")),
        ("AppleScript 'configure'", lambda: get_button_position("RustDesk", "configure")),
        ("OCR 'Configure'", lambda: find_text_by_ocr("Configure")),
        ("Fallback A", lambda: (960, 810)),
        ("Fallback B", lambda: (950, 800)),
        ("Fallback C", lambda: (970, 820)),
    ]

    for name, func in methods:
        log(f"  → {name}")
        pos = func()
        if pos:
            cliclick(*pos)
            time.sleep(4.5)
            ok, out, _ = applescript('''
                tell application "System Events"
                    if exists (first window whose title contains "Screen Recording") then
                        return "yes"
                    else
                        return "no"
                    end if
                end tell
            ''')
            if "yes" in out.lower():
                log("→ SUCCESS: Screen Recording dialog appeared")
                shot("02_configure_success.png")
                return True
        time.sleep(0.8)

    log("All Configure click attempts failed → opening Privacy & Security directly")
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"])
    time.sleep(6)
    shot("02_configure_fallback.png")
    return False

def toggle_rustdesk_in_settings():
    log("Trying to toggle RustDesk in System Settings")
    time.sleep(4)
    pos = find_text_by_ocr("RustDesk")
    if pos:
        # usually toggle is ~180–250 px to the right
        cliclick(pos[0] + 220, pos[1])
        log("Clicked approx toggle position using OCR")
    else:
        log("No RustDesk text found → using fallback toggle coord")
        cliclick(1480, 380)
    time.sleep(2.5)
    shot("04_after_toggle_attempt.png")

def handle_password_prompt():
    log("Looking for password prompt")
    ok, out, _ = applescript('''
        tell application "System Events"
            tell process "System Settings"
                if exists sheet 1 of window 1 then
                    try
                        keystroke "Apple@123"
                        delay 0.7
                        key code 36
                        delay 1.2
                        return "typed"
                    end try
                end if
            end tell
        end tell
        return "none"
    ''')
    if "typed" in out:
        log("Password entered")
    else:
        log("No password sheet detected")

# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────

log("=== RustDesk screen recording automation (2025 fixed version) ===")
shot("00_start.png")

start_allow_clicker()
time.sleep(1.5)

# Trigger initial TCC prompt for python/bash
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"], check=False)
time.sleep(4)
shot("01_after_initial_trigger.png")

# Main flow
click_configure()

toggle_rustdesk_in_settings()
handle_password_prompt()
shot("05_after_password.png")

# Try to quit & reopen if needed
applescript('''
    tell application "RustDesk" to quit
    delay 3
    tell application "RustDesk" to activate
''')
time.sleep(7)
shot("06_after_quit_reopen.png")

time.sleep(4)
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/rustdesk.png"], check=False)
shot("07_final.png")

stop_allow_clicker()

log("=== Automation finished ===")