#!/usr/bin/env python3
# Robust automation with verification & retries
import subprocess, time, pathlib, sys, os, signal

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
    """Click using cliclick (fallback to AppleScript if missing)."""
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=True, timeout=5)
        log(f"cliclick at ({x},{y})")
    except:
        log("cliclick failed, trying AppleScript click")
        applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def wait_for_no_dialogs(timeout=30):
    """Wait until no window contains an 'Allow' button."""
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

def click_configure():
    """Try multiple methods to click Configure, verify success."""
    log("Attempting to click 'Configure' in RustDesk...")
    # Method 1: AppleScript targeting button
    success, _ = applescript('''
        tell application "System Events"
            tell process "RustDesk"
                set frontmost to true
                try
                    click (first button of window 1 whose title is "Configure")
                    return "clicked"
                end try
            end tell
            return "failed"
        end tell
    ''')
    if success and "clicked" in _:
        log("AppleScript clicked Configure")
        return True
    # Method 2: cliclick at bottom center
    log("AppleScript failed, using cliclick fallback")
    cliclick(960, 810)
    time.sleep(2)
    # Verify: after click, should see permission dialog
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
        log("Configure click successful (dialog appeared)")
        return True
    log("Configure click may have failed – dialog not detected")
    return False

def click_open_system_settings():
    log("Looking for 'Open System Settings' button...")
    # AppleScript click
    success, _ = applescript('''
        tell application "System Events"
            try
                set theButton to first button of (first window whose title contains "Screen Recording") whose title contains "Open System Settings"
                click theButton
                return "clicked"
            end try
            return "failed"
        end tell
    ''')
    if success and "clicked" in _:
        log("AppleScript clicked Open System Settings")
        return True
    log("AppleScript failed, using fallback click at left-center")
    cliclick(760, 540)
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
        return True
    log("System Settings may not have opened")
    return False

def toggle_rustdesk_in_settings():
    log("Toggling RustDesk in System Settings...")
    # Wait for list to populate
    time.sleep(5)
    # Try OCR to find RustDesk text (if tesseract works)
    import re
    shot("pre_toggle.png")
    # Use cliclick at approximate toggle area (right side)
    cliclick(1500, 400)
    time.sleep(2)
    shot("post_toggle.png")
    log("Toggle clicked (assumed)")

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
    log("FATAL: Could not click Configure – aborting")
    stop_allow_clicker()
    sys.exit(1)
shot("02_after_configure.png")

# Wait for permission dialog and click Open System Settings
if not click_open_system_settings():
    log("FATAL: Could not open System Settings")
    stop_allow_clicker()
    sys.exit(1)
shot("03_after_open_settings.png")

# Step 3: Toggle RustDesk
toggle_rustdesk_in_settings()
shot("04_after_toggle.png")

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