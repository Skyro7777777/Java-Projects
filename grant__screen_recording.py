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

log("=== AnyDesk Screen Recording Automation ===")
shot("00_start.png")

# Trigger initial permission
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"])
time.sleep(4)
shot("01_after_trigger.png")

# Activate AnyDesk
applescript('tell application "AnyDesk" to activate')
time.sleep(4)

# Click the permission request button (standard title on AnyDesk macOS)
log("Clicking permission request button...")
applescript('''
    tell application "System Events"
        tell process "AnyDesk"
            try
                click (first button of window 1 whose title contains "Open Screen Recording" or title contains "Grant" or title contains "Request")
            end try
        end tell
    end tell
''')
time.sleep(6)
shot("02_after_permission_click.png")

# Click "Open System Preferences" / "Open System Settings" in the dialog
log("Opening System Settings from dialog...")
applescript('''
    tell application "System Events"
        click (first button of window 1 whose title contains "Open System" or title contains "Preferences" or title contains "Settings")
    end tell
''')
time.sleep(8)
shot("03_settings_opened.png")

# Toggle AnyDesk in Screen Recording pane
log("Toggling AnyDesk switch...")
cliclick(1480, 420)   # reliable position on GitHub runner
time.sleep(4)
shot("04_after_toggle.png")

# Password prompt if it appears
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

# Quit & reopen AnyDesk so permission takes effect
applescript('tell application "AnyDesk" to quit')
time.sleep(6)
applescript('tell application "AnyDesk" to activate')
time.sleep(12)
shot("07_final.png")

log("=== Done — check 07_final.png for AnyDesk ID ===")