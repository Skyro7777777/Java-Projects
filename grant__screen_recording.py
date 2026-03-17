#!/usr/bin/env python3
# Complete automation: clear popups, click RustDesk "Configure", grant permission, and capture final screenshot.
import subprocess, time, pathlib, sys, re

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)
TESSERACT = "/opt/homebrew/bin/tesseract"   # adjust if needed
CLICLICK = "/opt/homebrew/bin/cliclick"

def shot(name):
    path = DEBUG / name
    try:
        subprocess.run(["/usr/sbin/screencapture", "-x", str(path)], check=False)
    except Exception as e:
        print("screencapture error:", e)

def applescript(script):
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception as e:
        print("osascript error:", e)

def cliclick(x, y):
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=False)
    except:
        applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def ocr_find_text(target, timeout=30):
    """Return (x,y) center of first screen region containing target text, or None."""
    start = time.time()
    while time.time() - start < timeout:
        tmp = DEBUG / "ocr_tmp.png"
        subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp)], check=False)
        # run tesseract with bounding boxes
        base = tmp.with_suffix('')
        subprocess.run([TESSERACT, str(tmp), str(base), "tsv"], check=False, capture_output=True)
        tsv = base.with_suffix('.tsv')
        if tsv.exists():
            with open(tsv) as f:
                lines = f.readlines()
            tsv.unlink()
            for line in lines[1:]:
                parts = line.strip().split('\t')
                if len(parts) >= 12 and parts[11] and int(parts[10]) > 50:
                    text = parts[11].lower()
                    if target.lower() in text:
                        x = int(parts[6]) + int(parts[8])//2
                        y = int(parts[7]) + int(parts[9])//2
                        return (x, y)
        tmp.unlink()
        time.sleep(1)
    return None

# ----- START -----
shot("01_before_script.png")
print("Step 0: Aggressively clear any bash dialogs")
for i in range(8):
    applescript('''
    tell application "System Events"
        repeat with p in (every process)
            try
                repeat with w in (every window of p)
                    try
                        if exists button "Allow" of w then click button "Allow" of w
                    end try
                end repeat
            end try
        end repeat
    end tell
    ''')
    time.sleep(0.5)
shot("02_after_clear.png")

print("Step 1: Look for RustDesk 'Configure' button")
# First try OCR
pos = ocr_find_text("Configure", timeout=10)
if pos:
    print(f"Found 'Configure' at {pos}, clicking")
    cliclick(*pos)
else:
    print("OCR failed, using fallback coordinate (bottom center)")
    cliclick(960, 810)   # 1920x1080 screen, bottom center
time.sleep(3)
shot("03_after_configure_click.png")

print("Step 2: Click 'Open System Settings' in the permission dialog")
pos = ocr_find_text("Open System Settings", timeout=10)
if pos:
    cliclick(*pos)
else:
    print("Fallback: click left-center of screen")
    cliclick(760, 540)
time.sleep(5)
shot("04_after_open_settings.png")

print("Step 3: In System Settings, find and toggle RustDesk")
# Wait for RustDesk to appear in list (might take a few seconds)
pos = ocr_find_text("RustDesk", timeout=20)
if pos:
    # Click the toggle to the right of the text
    toggle_x = pos[0] + 200
    toggle_y = pos[1]
    cliclick(toggle_x, toggle_y)
    print(f"Clicked toggle at ({toggle_x}, {toggle_y})")
else:
    print("RustDesk not found, trying known toggle location (right side)")
    cliclick(1500, 400)   # approximate
time.sleep(2)
shot("05_after_toggle.png")

print("Step 4: Handle password prompt if it appears")
pos = ocr_find_text("Enter your password", timeout=5)
if pos:
    print("Password prompt detected")
    applescript(f'''
    tell application "System Events"
        keystroke "Apple@123"
        delay 1
        key code 36   -- return
    end tell
    ''')
    time.sleep(2)
    # Click "Modify Settings" if present
    pos2 = ocr_find_text("Modify Settings", timeout=3)
    if pos2:
        cliclick(*pos2)
shot("06_after_password.png")

print("Step 5: Handle 'Quit & Reopen' dialog")
pos = ocr_find_text("Quit", timeout=5)
if pos:
    cliclick(*pos)
    print("RustDesk quitting, waiting for restart...")
    time.sleep(8)
shot("07_after_quit.png")

print("Step 6: Final screenshot for OCR")
time.sleep(5)
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/rustdesk.png"], check=False)
shot("08_final.png")
print("Automation script completed.")