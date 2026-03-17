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

log("=== Remotix Agent Screen Recording Automation ===")
shot("00_start.png")

# Trigger initial permission
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"])
time.sleep(4)
shot("01_after_trigger.png")

# Launch Remotix Agent (already done in workflow, but ensure frontmost)
applescript('tell application "Remotix Agent" to activate')
time.sleep(3)

# Click the built-in "Request Screen Recording Permission" button (exact title!)
log("Clicking 'Request Screen Recording Permission' button...")
applescript('''
    tell application "System Events"
        tell process "Remotix Agent"
            click (first button of window 1 whose title contains "Request Screen Recording Permission")
        end tell
    end tell
''')
time.sleep(5)
shot("02_after_request_button.png")

# The dialog should now be open → click "Open System Preferences"
log("Clicking 'Open System Preferences' in dialog...")
applescript('''
    tell application "System Events"
        click (first button of window 1 whose title contains "Open System Preferences")
    end tell
''')
time.sleep(6)
shot("03_settings_opened.png")

# In Screen Recording pane → toggle Remotix Agent (or click + if needed)
log("Toggling Remotix Agent in settings...")
cliclick(1480, 420)  # switch position on runner
time.sleep(3)
shot("04_after_toggle.png")

# Password prompt if appears
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

# Quit & reopen Remotix Agent
applescript('tell application "Remotix Agent" to quit')
time.sleep(5)
applescript('tell application "Remotix Agent" to activate')
time.sleep(10)
shot("07_final.png")

log("=== Done - check 07_final.png for Remotix Agent ID ===")