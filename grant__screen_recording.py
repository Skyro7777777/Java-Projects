#!/usr/bin/env python3
# Robust automation with OCR & AppleScript location for Configure button
import subprocess, time, pathlib, sys, os, signal, re

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK = "/opt/homebrew/bin/cliclick"
clicker_proc = None

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

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
                                delay 0.5
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
    """Run AppleScript, return (success, output)."""
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
    time.sleep(3)
    if wait_for_no_dialogs(15):
        log("Bash permission granted")
    else:
        log("Bash permission may not be fully granted, continuing")

def get_button_position_by_title(app_name, button_title):
    """AppleScript to get (x,y) of button with given title in app's front window."""
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontmost to true
            try
                set theButton to first button of window 1 whose title is "{button_title}"
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

def find_configure_by_ocr():
    """Use tesseract to locate 'Configure' on screen, return center coordinates."""
    shot("ocr_search.png")
    # Run tesseract with bounding boxes
    tmp_img = DEBUG / "ocr_tmp.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp_img)], check=False)
    base = tmp_img.with_suffix('')
    subprocess.run([TESSERACT, str(tmp_img), str(base), "tsv"], check=False, capture_output=True)
    tsv = base.with_suffix('.tsv')
    if tsv.exists():
        with open(tsv) as f:
            lines = f.readlines()
        tsv.unlink()
        tmp_img.unlink()
        for line in lines[1:]:
            parts = line.strip().split('\t')
            if len(parts) >= 12 and parts[11] and int(parts[10]) > 50:
                text = parts[11].lower()
                if "configure" in text:
                    x = int(parts[6]) + int(parts[8])//2
                    y = int(parts[7]) + int(parts[9])//2
                    log(f"Found 'Configure' via OCR at ({x},{y})")
                    return (x, y)
    log("OCR did not find 'Configure'")
    return None

def click_configure():
    """Try multiple methods to click Configure, return True if successful."""
    log("Attempting to click 'Configure' in RustDesk...")
    methods = [
        ("AppleScript position", lambda: get_button_position_by_title("RustDesk", "Configure")),
        ("AppleScript position (lowercase)", lambda: get_button_position_by_title("RustDesk", "configure")),
        ("AppleScript position (process rustdesk)", lambda: get_button_position_by_title("rustdesk", "Configure")),
        ("OCR", find_configure_by_ocr),
        ("Fallback coordinate (960,810)", lambda: (960, 810)),
        ("Fallback coordinate (950,800)", lambda: (950, 800)),
        ("Fallback coordinate (970,820)", lambda: (970, 820)),
    ]
    for method_name, method_func in methods:
        log(f"Trying method: {method_name}")
        pos = method_func()
        if pos:
            x, y = pos
            cliclick(x, y)
            time.sleep(3)
            # Verify if permission dialog appeared
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
                log("Dialog not detected after click, trying next method")
        else:
            log(f"Method {method_name} returned no position")
    log("All methods failed to click Configure")
    shot("02_after_configure_failed.png")
    return False

def click_open_system_settings():
    log("Looking for 'Open System Settings' button...")
    # Similar multi-method approach
    methods = [
        ("AppleScript by title", lambda: get_button_position_by_title("System Events", "Open System Settings")),
        ("OCR", lambda: find_text_by_ocr("Open System Settings")),
        ("Fallback (760,540)", lambda: (760, 540)),
    ]
    for method_name, method_func in methods:
        log(f"Trying method: {method_name}")
        pos = method_func()
        if pos:
            cliclick(*pos)
            time.sleep(3)
            # Verify System Settings opened
            ok, out = applescript('''
                tell application "System Events"
                    if exists process "System Settings" then return "yes"
                    return "no"
                end tell
            ''')
            if out == "yes":
                log("System Settings opened")
                shot("03_after_open_settings_success.png")
                return True
    log("Failed to open System Settings")
    shot("03_after_open_settings_failed.png")
    return False

def find_text_by_ocr(target):
    # Same as find_configure_by_ocr but generic
    tmp_img = DEBUG / "ocr_tmp2.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp_img)], check=False)
    base = tmp_img.with_suffix('')
    subprocess.run([TESSERACT, str(tmp_img), str(base), "tsv"], check=False, capture_output=True)
    tsv = base.with_suffix('.tsv')
    if tsv.exists():
        with open(tsv) as f:
            lines = f.readlines()
        tsv.unlink()
        tmp_img.unlink()
        target_lower = target.lower()
        for line in lines[1:]:
            parts = line.strip().split('\t')
            if len(parts) >= 12 and parts[11] and int(parts[10]) > 50:
                text = parts[11].lower()
                if target_lower in text:
                    x = int(parts[6]) + int(parts[8])//2
                    y = int(parts[7]) + int(parts[9])//2
                    log(f"Found '{target}' via OCR at ({x},{y})")
                    return (x, y)
    log(f"OCR did not find '{target}'")
    return None

def toggle_rustdesk_in_settings():
    log("Toggling RustDesk in System Settings...")
    time.sleep(5)
    # Try to find the toggle via OCR or coordinates
    pos = find_text_by_ocr("RustDesk")
    if pos:
        toggle_x = pos[0] + 200
        toggle_y = pos[1]
        cliclick(toggle_x, toggle_y)
        log("Clicked toggle based on RustDesk text position")
    else:
        log("Using fallback toggle position (1500,400)")
        cliclick(1500, 400)
    time.sleep(2)
    shot("04_after_toggle.png")

def handle_password():
    log("Checking for password prompt...")
    success, _ = applescript('''
        tell application "System Events"
            if exists (first window whose title contains "Privacy & Security" and exists button "Modify Settings") then
                keystroke "Apple@123"
                delay 1
                key code 36
                delay 1
                click (first button whose title is "Modify Settings")
                return "handled"
            end if
            return "none"
        end tell
    ''')
    if "handled" in _:
        log("Password prompt handled")
    else:
        log("No password prompt detected")

def handle_quit_reopen():
    log("Looking for 'Quit' dialog...")
    success, _ = applescript('''
        tell application "System Events"
            try
                click (first button of (first window whose title contains "RustDesk") whose title is "Quit")
                return "quit_clicked"
            end try
            return "no_quit"
        end tell
    ''')
    if "quit_clicked" in _:
        log("Quit clicked, waiting for restart")
        time.sleep(8)
    else:
        log("No quit dialog (already allowed?)")

# ---------- MAIN ----------
log("=== Starting automation ===")
shot("00_start.png")

start_allow_clicker()
time.sleep(1)

# Step 0: Grant bash permission
trigger_and_grant_bash()
shot("01_after_bash.png")

# Step 1: Click Configure
if not click_configure():
    log("WARNING: Could not click Configure – will try to continue but may fail")
    # We'll continue anyway to capture more debug info

# Step 2: Click Open System Settings
if not click_open_system_settings():
    log("WARNING: Could not open System Settings")

# Step 3: Toggle RustDesk
toggle_rustdesk_in_settings()

# Step 4: Password
handle_password()
shot("05_after_password.png")

# Step 5: Quit & Reopen
handle_quit_reopen()
shot("06_after_quit.png")

# Step 6: Final screenshot
time.sleep(5)
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/rustdesk.png"], check=False)
shot("07_final.png")

stop_allow_clicker()
log("=== Automation completed ===")