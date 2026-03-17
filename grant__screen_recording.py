#!/usr/bin/env python3
# grant__screen_recording.py - Full version with no ImageMagick dependency

import subprocess
import time
import pathlib
import sys
import os
import signal

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK = "/opt/homebrew/bin/cliclick"
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
    log("Background clicker started")

def stop_allow_clicker():
    if clicker_proc:
        clicker_proc.terminate()
        clicker_proc.wait()
        log("Background clicker stopped")

def shot(name):
    path = DEBUG / name
    subprocess.run(["/usr/sbin/screencapture", "-x", str(path)], check=False)
    log(f"Screenshot saved: {name}")

def applescript(script, check=False):
    result = subprocess.run(['osascript', '-e', script],
                            capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"AppleScript error: {result.stderr}")
    return result.returncode == 0, result.stdout.strip()

def cliclick(x, y):
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=True, timeout=5)
        log(f"cliclick at ({x},{y})")
    except:
        log("cliclick failed, trying AppleScript click")
        applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def wait_for_no_dialogs(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        ok, out = applescript('''
            tell application "System Events"
                set found to false
                repeat with p in (every process)
                    try
                        repeat with w in (every window of p)
                            if exists button "Allow" of w then
                                set found to true
                                exit repeat
                            end if
                        end repeat
                    end try
                end repeat
                return found
            end tell
        ''')
        if out == "false":
            log("No 'Allow' dialogs left")
            return True
        time.sleep(1)
    log("Warning: dialogs still present after timeout")
    return False

def trigger_and_grant_bash():
    log("Triggering bash permission...")
    subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"], check=False)
    time.sleep(4)
    if wait_for_no_dialogs(20):
        log("Bash permission granted")
    else:
        log("Bash permission may not be fully granted, continuing")

def get_button_position_by_title(app_name, button_title):
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontmost to true
            try
                set theButton to first button of window 1 whose title contains "{button_title}"
                set btnPosition to position of theButton
                set btnSize to size of theButton
                return (item 1 of btnPosition + (item 1 of btnSize) / 2) & "," & (item 2 of btnPosition + (item 2 of btnSize) / 2)
            on error
                return "not found"
            end try
        end tell
    end tell
    '''
    ok, out = applescript(script)
    if ok and out != "not found" and ',' in out:
        x, y = map(int, out.split(','))
        log(f"Found '{button_title}' at ({x},{y}) via AppleScript")
        return (x, y)
    return None

def find_text_by_ocr(target):
    tmp_img = DEBUG / "ocr_tmp.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp_img)], check=False)
    base = tmp_img.with_suffix('')
    subprocess.run([TESSERACT, str(tmp_img), str(base), "--psm", "7", "tsv"], check=False, capture_output=True)
    tsv = base.with_suffix('.tsv')
    if tsv.exists():
        with open(tsv) as f:
            lines = f.readlines()
        for p in [tsv, tmp_img]:
            p.unlink(missing_ok=True)
        target_lower = target.lower()
        for line in lines[1:]:
            parts = line.strip().split('\t')
            if len(parts) >= 12 and parts[11] and int(parts[10]) > 30:
                text = parts[11].lower()
                if target_lower in text:
                    x = int(parts[6]) + int(parts[8])//2
                    y = int(parts[7]) + int(parts[9])//2
                    log(f"Found '{target}' via OCR at ({x},{y})")
                    return (x, y)
    log(f"OCR did not find '{target}'")
    return None

def click_configure():
    log("Attempting to click 'Configure' in RustDesk...")
    applescript('tell application "RustDesk" to activate')
    time.sleep(2)
    methods = [
        ("AppleScript position", lambda: get_button_position_by_title("RustDesk", "Configure")),
        ("OCR", lambda: find_text_by_ocr("Configure")),
        ("Fallback pink area 1", lambda: (280, 720)),
        ("Fallback pink area 2", lambda: (320, 710)),
        ("Fallback pink area 3", lambda: (250, 740)),
        ("Fallback pink area 4", lambda: (360, 690)),
    ]
    for method_name, method_func in methods:
        log(f"Trying method: {method_name}")
        pos = method_func()
        if pos:
            x, y = pos
            cliclick(x, y)
            time.sleep(5)
            ok, out = applescript('''
                tell application "System Events"
                    if exists (first window whose title contains "Screen Recording") then
                        return "dialog_found"
                    else
                        return "no_dialog"
                    end if
                end tell
            ''')
            if "dialog_found" in out:
                log("Configure click successful – dialog detected")
                shot("02_after_configure_success.png")
                return True
            else:
                log("Dialog not detected after click")
        else:
            log(f"Method {method_name} returned no position")
    log("All methods failed to click Configure - falling back to direct settings")
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"])
    time.sleep(7)
    shot("02_after_configure_fallback.png")
    return False

def add_rustdesk_to_settings():
    log("Attempting to add RustDesk in System Settings via + button...")
    time.sleep(5)
    # Try AppleScript to click + button
    applescript('''
        tell application "System Events"
            tell process "System Settings"
                try
                    click button "+" of scroll area 1 of group 1 of window 1
                end try
            end tell
        end tell
    ''')
    time.sleep(4)
    # Type path and confirm (approximate dialog handling)
    applescript('''
        tell application "System Events"
            keystroke "/Applications/RustDesk.app"
            delay 1.5
            key code 36
            delay 2
            key code 36
        end tell
    ''')
    time.sleep(4)
    shot("04_after_add_attempt.png")

# ---------- MAIN ----------
log("=== Starting automation (full version) ===")
shot("00_start.png")

start_allow_clicker()
time.sleep(1)

trigger_and_grant_bash()
shot("01_after_bash.png")

click_configure()

add_rustdesk_to_settings()

# Handle possible password prompt
applescript('''
    tell application "System Events"
        if exists (first window whose title contains "Privacy & Security") then
            keystroke "Apple@123"
            delay 1
            key code 36
        end if
    end tell
''')
time.sleep(3)
shot("05_after_password.png")

# Quit and reopen RustDesk
applescript('tell application "RustDesk" to quit')
time.sleep(5)
applescript('tell application "RustDesk" to activate')
time.sleep(8)
shot("06_after_quit_reopen.png")

# Final screenshot
time.sleep(4)
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/rustdesk.png"], check=False)
shot("07_final.png")

stop_allow_clicker()
log("=== Automation completed ===")