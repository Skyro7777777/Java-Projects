#!/usr/bin/env python3
# Best-effort UI automation: click Allow/Open System Settings, open System Settings,
# search for "RustDesk", try to toggle switch, and save debug screenshots.
import subprocess, time, pathlib

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

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

# 0) initial
shot("02_start.png")

# 1) aggressively click standard dialog buttons ("Allow", "Open System Settings", "Open System Preferences")
for i in range(12):
    script = '''
    tell application "System Events"
      repeat with p in (every process)
        try
          repeat with w in (every window of p)
            try
              repeat with b in {"Allow","Open System Settings","Open System Preferences"}
                try
                  if exists button b of w then
                    click button b of w
                    delay 0.6
                  end if
                end try
              end repeat
            end try
          end repeat
        end try
      end repeat
    end tell
    '''
    applescript(script)
    shot(f"03_clear_{i}.png")
    time.sleep(0.7)

# 2) open System Settings (macOS 13+/14+)
applescript('tell application "System Settings" to activate')
time.sleep(2)
shot("04_settings_opened.png")

# 3) attempt to search RustDesk (send keystrokes)
applescript('tell application "System Events" to keystroke "RustDesk"')
time.sleep(2)
shot("05_search_typed.png")

# 4) try cliclick coordinate fallback positions (common area for toggles)
cands = [(1000,360),(1100,420),(1200,480),(900,420)]
for x,y in cands:
    # prefer installed cliclick binary
    try:
        subprocess.run(["/usr/local/bin/cliclick", f"c:{x},{y}"], check=False)
    except Exception:
        try:
            subprocess.run(["/opt/homebrew/bin/cliclick", f"c:{x},{y}"], check=False)
        except Exception:
            # apple-script coordinate click fallback
            applescript(f'tell application "System Events" to click at {{{x},{y}}}')
    time.sleep(0.6)
    shot(f"06_click_{x}_{y}.png")

# 5) another pass to clear any remaining dialogs
for i in range(6):
    applescript(script)
    shot(f"07_posttoggle_{i}.png")
    time.sleep(0.7)

# 6) final screenshots
shot("08_final_system.png")
# take /tmp/rustdesk.png for OCR later
try:
    subprocess.run(["/usr/sbin/screencapture","-x","/tmp/rustdesk.png"], check=False)
except Exception as e:
    print("final screencapture failed:", e)
print("Automation script done")
