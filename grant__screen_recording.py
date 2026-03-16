#!/usr/bin/env python3
"""
Best-effort automation to accept macOS screen-recording permission dialogs
for RustDesk. Uses AppleScript (System Events) to click dialog buttons and
navigates System Settings. Keeps debug screenshots for diagnostics.

Caveats: macOS TCC is designed to require explicit user approval. This script
is a UI-automation best-effort and may not work in all runner images.
"""

import subprocess, time, tempfile, os, sys, shutil, re
from pathlib import Path

USER_PASSWORD = "Apple@123"
SCREENSHOT_DIR = Path("/tmp")
DEBUG_DIR = SCREENSHOT_DIR / "debug_screenshots"
DEBUG_DIR.mkdir(exist_ok=True)

TESSERACT = shutil.which("tesseract") or "/usr/bin/tesseract"
CLICLICK = shutil.which("cliclick") or "/usr/local/bin/cliclick"
SCREENCAPTURE = shutil.which("screencapture") or "/usr/sbin/screencapture"

def run_cmd(cmd, capture=False, timeout=60):
    if isinstance(cmd, list):
        p = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    else:
        p = subprocess.run(cmd, shell=True, capture_output=capture, text=True, timeout=timeout)
    if capture:
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    return p.returncode

def save_debug(name):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = DEBUG_DIR / f"{name}_{timestamp}.png"
    try:
        run_cmd(f'{SCREENCAPTURE} -x "{path}"')
    except Exception as e:
        print("Could not take debug screenshot:", e)
    print("Saved debug:", path)

def run_applescript(script):
    """Run an AppleScript string and return (stdout, stderr, rc)."""
    proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def click_all_permission_buttons(buttons=("Allow","Open System Settings","Open System Preferences")):
    """
    Loop through all processes and click named buttons on windows/sheets.
    Returns True if any click was made.
    """
    apple = '''
    tell application "System Events"
      set clickedSomething to false
      repeat with proc in (every process)
        try
          repeat with w in (every window of proc)
            try
              repeat with bname in {%s}
                try
                  set theButtons to (every button whose name is bname of w)
                  repeat with bb in theButtons
                    click bb
                    set clickedSomething to true
                    delay 0.6
                  end repeat
                end try
              end repeat
            end try
          end repeat
        end try
      end repeat
      return clickedSomething
    end tell
    ''' % (','.join('"%s"' % b for b in buttons))
    out, err, rc = run_applescript(apple)
    return (out.lower() == "true")

def open_system_settings_and_select_privacy_screen_recording():
    """
    Try to open System Settings > Privacy & Security > Screen Recording
    and find RustDesk row.
    """
    # try to launch System Settings and reveal Security & Privacy pane (works on many macOS versions)
    reveal = 'tell application "System Settings" to activate'
    run_applescript(reveal)
    time.sleep(2)
    save_debug("systemsettings_opened")

    # Try to click search field and type "RustDesk"
    # Use System Events keystrokes to search and then press return to reveal row
    search_script = '''
    tell application "System Events"
      tell process "System Settings"
        try
          set frontmost to true
          -- try to find search field (varies by macOS version)
          try
            click (first text field of window 1)
          on error
            try
              click (first text field whose description contains "search" of window 1)
            end try
          end try
          delay 0.5
        end try
      end tell
    end tell
    '''
    run_applescript(search_script)
    time.sleep(0.4)

    # type "RustDesk" via osascript keystrokes
    run_cmd(['osascript','-e', 'tell application "System Events" to keystroke "RustDesk"'])
    time.sleep(1)
    save_debug("search_typed")

    # Wait briefly for results to appear
    time.sleep(2)
    save_debug("after_search")

def try_toggle_rustdesk_switch():
    """
    Attempt to find a row named RustDesk in System Settings and click the switch next to it.
    This uses System Events UI scripting to search windows' UI elements.
    """
    apple = '''
    tell application "System Events"
      tell process "System Settings"
        set frontmost to true
        delay 0.5
        try
          repeat with w in (every window)
            try
              -- look for any static text containing RustDesk
              set rustElems to (every static text of w whose value contains "RustDesk")
              if (count of rustElems) > 0 then
                repeat with r in rustElems
                  try
                    set bounds_r to (position of r)
                    -- attempt to click a UI element to the right (a button or checkbox)
                    -- find clickable elements in the same window and click the first one to the right
                    set allBtns to (every button of w)
                    if (count of allBtns) > 0 then
                      click item 1 of allBtns
                      return "clicked"
                    end if
                  end try
                end repeat
              end if
            end try
          end repeat
        end try
      end tell
    end tell
    return "done"
    '''
    out, err, rc = run_applescript(apple)
    return out

def fallback_click_coords():
    """
    Last-resort fallback: click near center-right where a permission toggle is commonly located.
    Coordinates assume 1440x900-ish screen in runners; adapt as needed.
    """
    # try to get screen size and scale coordinates
    out, err, rc = run_cmd("system_profiler SPDisplaysDataType | grep Resolution", capture=True)
    width, height = 1440, 900
    m = re.search(r'(\d+)\s*x\s*(\d+)', out)
    if m:
        width = int(m.group(1)); height = int(m.group(2))
    # click a few candidate positions (right side where switches are)
    cand = [(int(width*0.8), int(height*0.35)), (int(width*0.8), int(height*0.45)), (int(width*0.8), int(height*0.55))]
    for x,y in cand:
        try:
          if shutil.which("cliclick"):
            run_cmd(f'cliclick c:{x},{y}')
          else:
            # fallback to AppleScript clicking at coordinates
            run_applescript(f'tell application "System Events" to click at {{{x},{y}}}')
        except Exception as e:
          print("fallback click error", e)
        time.sleep(0.6)
        save_debug(f"fallback_click_{x}_{y}")

def main():
    print("Starting permission automation (best-effort).")
    save_debug("start")

    # Step A: aggressively click "Allow" & "Open System Settings" buttons until they stop appearing
    for i in range(12):
        clicked = click_all_permission_buttons()
        print(f"Pass {i+1}: clicked permission button? {clicked}")
        save_debug(f"clear_pass_{i+1}")
        if not clicked:
            break
        time.sleep(0.6)

    # Step B: if any "Open System Settings" button remains, click it
    # We attempted above; wait and then try AppleScript-specific clicks by exact button names in sheets
    time.sleep(1)

    # Step C: open System Settings and search for RustDesk
    open_system_settings_and_select_privacy_screen_recording()
    time.sleep(1)

    # Step D: try to toggle RustDesk switch using UI scripting
    res = try_toggle_rustdesk_switch()
    print("try_toggle_rustdesk_switch result:", res)
    save_debug("after_try_toggle")

    # Step E: if the above didn't obviously toggle, fallback click coords
    fallback_click_coords()

    # Step F: final screenshot and done
    save_debug("final")
    print("Done. Check debug screenshots in /tmp/debug_screenshots for details.")
    print("If this fails, manual intervention or an MDM/profile that pre-approves screen-recording is required.")

if __name__ == "__main__":
    main()