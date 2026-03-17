#!/usr/bin/env python3
# Fixed version: TCC reset + better detection + OCR preprocessing + Sequoia fixes
import subprocess, time, pathlib, sys, os

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK = "/opt/homebrew/bin/cliclick"
CONVERT = "/opt/homebrew/bin/convert"
clicker_proc = None

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def start_allow_clicker():
    global clicker_proc
    # (unchanged - your original background Allow clicker - it already works)

def stop_allow_clicker():
    # (unchanged)

def shot(name):
    # (unchanged)

def applescript(script, check=False):
    # (unchanged)

def cliclick(x, y):
    # (unchanged)

def activate_rustdesk():
    log("Activating RustDesk window")
    applescript('tell application "RustDesk" to activate')
    time.sleep(2)

def get_button_position_by_title(app_name, button_title):
    """Improved: uses 'contains' + explicit frontmost"""
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

def preprocess_for_ocr(img_path):
    """ImageMagick preprocess for better OCR on buttons"""
    pre = img_path.with_suffix('.pre.png')
    subprocess.run([CONVERT, str(img_path), "-colorspace", "Gray", "-normalize", "-threshold", "55%", str(pre)], check=False)
    return pre

def find_configure_by_ocr():
    shot("ocr_search.png")
    tmp_img = DEBUG / "ocr_tmp.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp_img)], check=False)
    pre_img = preprocess_for_ocr(tmp_img)
    base = pre_img.with_suffix('')
    subprocess.run([TESSERACT, str(pre_img), str(base), "--psm", "7", "tsv"], check=False, capture_output=True)
    tsv = base.with_suffix('.tsv')
    if tsv.exists():
        with open(tsv) as f:
            lines = f.readlines()
        # cleanup
        for p in [tsv, pre_img, tmp_img]:
            p.unlink(missing_ok=True)
        for line in lines[1:]:
            parts = line.strip().split('\t')
            if len(parts) >= 12 and parts[11] and int(parts[10]) > 30:  # lower confidence threshold
                text = parts[11].lower()
                if "configure" in text:
                    x = int(parts[6]) + int(parts[8])//2
                    y = int(parts[7]) + int(parts[9])//2
                    log(f"Found 'Configure' via OCR at ({x},{y})")
                    return (x, y)
    log("OCR did not find 'Configure'")
    return None

def click_configure():
    log("Attempting to click 'Configure' in RustDesk...")
    activate_rustdesk()
    methods = [
        ("AppleScript contains", lambda: get_button_position_by_title("RustDesk", "Configure")),
        ("AppleScript lowercase", lambda: get_button_position_by_title("RustDesk", "configure")),
        ("OCR (preprocessed)", find_configure_by_ocr),
        ("Fallback center-ish", lambda: (960, 810)),
        ("Fallback alt1", lambda: (950, 800)),
        ("Fallback alt2", lambda: (970, 820)),
    ]
    for method_name, method_func in methods:
        log(f"Trying method: {method_name}")
        pos = method_func()
        if pos:
            x, y = pos
            cliclick(x, y)
            time.sleep(4)
            # verify dialog
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
                log("Configure click SUCCESS – dialog detected")
                shot("02_after_configure_success.png")
                return True
    log("All methods failed - falling back to direct System Settings")
    shot("02_after_configure_failed.png")
    # direct fallback
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"])
    time.sleep(5)
    return False

# (rest of your functions unchanged: click_open_system_settings, find_text_by_ocr (add preprocess + --psm 7), toggle_rustdesk_in_settings, handle_password, handle_quit_reopen)

# ---------- MAIN ----------
log("=== Starting automation (fixed version) ===")
shot("00_start.png")

start_allow_clicker()
time.sleep(2)

trigger_and_grant_bash()  # your original
shot("01_after_bash.png")

if not click_configure():
    log("WARNING: Configure failed - using direct settings fallback")

# (rest of your main steps unchanged: open settings, toggle, password, quit/reopen, final shot)

stop_allow_clicker()
log("=== Automation completed ===")