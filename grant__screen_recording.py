#!/usr/bin/env python3
import subprocess
import time
import pathlib

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

CLICLICK = "/opt/homebrew/bin/cliclick"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def shot(name):
    subprocess.run(["/usr/sbin/screencapture", "-x", str(DEBUG / name)], check=False)
    log(f"Screenshot: {name}")

def applescript(code):
    r = subprocess.run(['osascript', '-e', code], capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip()

def cliclick(x, y):
    subprocess.run([CLICLICK, f"c:{x},{y}"], timeout=8, check=False)
    log(f"Clicked ({x},{y})")

log("=== AnyDesk Permissions Automation (exact screenshot flow) ===")
shot("00_start.png")

# Activate the permissions status window
applescript('tell application "AnyDesk" to activate')
time.sleep(3)
shot("01_status_window.png")

# Click the two required buttons from your screenshot
log("Clicking 'Open Screen Recording preferences'...")
applescript('''
    tell application "System Events"
        tell process "AnyDesk"
            click (first button of window 1 whose title contains "Open Screen Recording preferences")
        end tell
    end tell
''')
time.sleep(6)
shot("02_screen_recording_opened.png")

log("Clicking 'Request Accessibility'...")
applescript('''
    tell application "System Events"
        click (first button of window 1 whose title contains "Request Accessibility")
    end tell
''')
time.sleep(6)
shot("03_accessibility_requested.png")

# Now in System Settings pane → add AnyDesk via + button
log("Adding AnyDesk via + button...")
applescript('''
    tell application "System Events"
        tell process "System Settings"
            click button "+" of scroll area 1 of group 1 of window 1
        end tell
    end tell
''')
time.sleep(4)

applescript('''
    tell application "System Events"
        keystroke "/Applications/AnyDesk.app"
        delay 1.5
        key code 36
        delay 2
        key code 36
    end tell
''')
time.sleep(6)
shot("04_after_add.png")

# Toggle the switch (right side of the list)
cliclick(1480, 420)
time.sleep(4)
shot("05_after_toggle.png")

# Password prompt
applescript('''
    tell application "System Events"
        if exists (button "Modify Settings") then
            keystroke "Apple@123"
            delay 1
            key code 36
        end if
    end tell
''')
time.sleep(4)
shot("06_after_password.png")

# Quit & reopen so main ID window appears (connection info visible)
applescript('tell application "AnyDesk" to quit')
time.sleep(6)
applescript('tell application "AnyDesk" to activate')
time.sleep(12)
shot("07_final_anydesk.png")

log("=== Automation finished — ID should now be visible in 07_final_anydesk.png ===")