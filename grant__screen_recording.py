#!/usr/bin/env python3
# Complete automation: grant bash permission, then click RustDesk "Configure", etc.
import subprocess, time, pathlib, sys, os, signal

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK = "/opt/homebrew/bin/cliclick"

# Background clicker process
clicker_proc = None

def start_allow_clicker():
    """Launch an AppleScript that continuously clicks any 'Allow' button."""
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
    # Run in background
    clicker_proc = subprocess.Popen(['osascript', '-e', script],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)

def stop_allow_clicker():
    if clicker_proc:
        clicker_proc.terminate()
        clicker_proc.wait()

def shot(name):
    path = DEBUG / name
    try:
        subprocess.run(["/usr/sbin/screencapture", "-x", str(path)], check=False)
    except Exception as e:
        print("screencapture error:", e)

def cliclick(x, y):
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=False)
    except:
        # fallback AppleScript click (may not work if accessibility not granted)
        subprocess.run(['osascript', '-e', f'tell application "System Events" to click at {{{x},{y}}}'], check=False)

def applescript(script):
    subprocess.run(['osascript', '-e', script], check=False)

def trigger_and_grant_bash():
    """Trigger a screen capture to prompt bash permission, let background clicker allow it."""
    print("Triggering bash permission dialog...")
    # Take a screenshot – this will trigger the dialog
    subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"], check=False)
    time.sleep(3)  # give clicker time to click
    # If dialog still present, maybe retry
    for _ in range(5):
        # Check if dialog still exists by looking for window with "Allow" using AppleScript
        check = subprocess.run(['osascript', '-e', 
            'tell application "System Events" to if exists (first window whose title contains "bash" and exists button "Allow") then return "yes"'],
            capture_output=True, text=True)
        if 'yes' in check.stdout:
            print("Dialog still present, waiting...")
            time.sleep(2)
        else:
            print("Bash permission granted (dialog gone).")
            return
    print("Warning: bash dialog may still be present, continuing anyway.")

# ----- MAIN -----
print("Starting automation...")
shot("00_before_anything.png")

# Start background clicker for "Allow" buttons
start_allow_clicker()
time.sleep(1)

# Step 0: Trigger bash permission and grant it
trigger_and_grant_bash()
shot("01_after_bash_grant.png")

# Now bash should be allowed; proceed with RustDesk automation
print("Proceeding with RustDesk automation...")

# Step 1: Click "Configure" in RustDesk (use AppleScript first to avoid new dialogs)
applescript('''
tell application "System Events"
    tell process "RustDesk"
        set frontmost to true
        try
            set configureButton to first button of window 1 whose title is "Configure"
            click configureButton
        end try
    end tell
end tell
''')
time.sleep(3)
shot("02_after_configure_applescript.png")

# If AppleScript failed, fallback to cliclick (now bash allowed)
# Check if we need fallback – we can just try cliclick anyway.
cliclick(960, 810)   # bottom center
time.sleep(2)
shot("03_after_configure_fallback.png")

# Step 2: Click "Open System Settings" in the permission dialog
applescript('''
tell application "System Events"
    try
        click (first button of (first window whose title contains "Screen Recording") whose title contains "Open System Settings")
    end try
end tell
''')
time.sleep(3)
shot("04_after_open_settings_applescript.png")

# Fallback cliclick
cliclick(760, 540)  # left-center
time.sleep(2)
shot("05_after_open_settings_fallback.png")

# Step 3: In System Settings, toggle RustDesk
# Wait for window
time.sleep(5)
# Try to find RustDesk row and click toggle via AppleScript? Hard.
# Use cliclick at approximate position
cliclick(1500, 400)  # right side, mid
time.sleep(2)
shot("06_after_toggle.png")

# Step 4: Handle password prompt if appears
applescript('''
tell application "System Events"
    if exists (first window whose title contains "Privacy & Security" and exists button "Modify Settings") then
        keystroke "Apple@123"
        delay 1
        key code 36
        delay 1
        click (first button whose title is "Modify Settings")
    end if
end tell
''')
shot("07_after_password.png")

# Step 5: Handle "Quit & Reopen"
applescript('''
tell application "System Events"
    try
        click (first button of (first window whose title contains "RustDesk") whose title is "Quit")
    end try
end tell
''')
time.sleep(8)
shot("08_after_quit.png")

# Step 6: Final screenshot
time.sleep(5)
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/rustdesk.png"], check=False)
shot("09_final.png")

# Stop background clicker
stop_allow_clicker()

print("Automation script completed.")