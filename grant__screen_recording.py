#!/usr/bin/env python3
"""
AnyDesk Automation Script – Grants Screen Recording & Accessibility permissions,
and sets up Unattended Access with password Apple@123.
All steps are logged and debug screenshots are saved.
"""

import subprocess
import time
import pathlib
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEBUG_DIR = pathlib.Path("/tmp/debug_screenshots")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = "/tmp/anydesk_automation.log"
CLICLICK = "/opt/homebrew/bin/cliclick"
UNATTENDED_PASSWORD = "Apple@123"
ANYDESK_APP = "/Applications/AnyDesk.app"
ANYDESK_BIN = f"{ANYDESK_APP}/Contents/MacOS/AnyDesk"

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
logger = logging.getLogger("AnyDeskAutomation")
logger.setLevel(logging.DEBUG)

# Console handler (prints to stdout)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logger.addHandler(console)

# File handler (rotates, keeps last 5 MB)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_info(msg):
    logger.info(msg)

def log_error(msg):
    logger.error(msg)

def log_debug(msg):
    logger.debug(msg)

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def shot(name):
    """Take a screenshot and save to DEBUG_DIR."""
    path = DEBUG_DIR / name
    try:
        subprocess.run(["/usr/sbin/screencapture", "-x", str(path)], check=False, timeout=10)
        log_debug(f"Screenshot saved: {name}")
    except Exception as e:
        log_error(f"screencapture failed for {name}: {e}")

def run_applescript(script, max_retries=1):
    """
    Run AppleScript, return (success, output).
    If it fails and max_retries > 1, retry after a short delay.
    """
    for attempt in range(max_retries):
        try:
            result = subprocess.run(['osascript', '-e', script],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                log_debug(f"AppleScript attempt {attempt+1} failed: {result.stderr}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        except subprocess.TimeoutExpired:
            log_error("AppleScript timed out")
            if attempt < max_retries - 1:
                time.sleep(2)
    return False, ""

def cliclick(x, y):
    """Click at (x,y) using cliclick; fallback to AppleScript click."""
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=True, timeout=8)
        log_debug(f"cliclick at ({x},{y})")
    except Exception:
        log_debug(f"cliclick failed, trying AppleScript click at ({x},{y})")
        run_applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def wait_for_window(process_name, window_title_contains, timeout=20):
    """Wait until a window with title containing substring appears."""
    start = time.time()
    while time.time() - start < timeout:
        ok, out = run_applescript(f'''
            tell application "System Events"
                if exists process "{process_name}" then
                    tell process "{process_name}"
                        if exists (first window whose title contains "{window_title_contains}") then
                            return "found"
                        end if
                    end tell
                end if
                return "not found"
            end tell
        ''')
        if "found" in out:
            return True
        time.sleep(1)
    return False

def click_button(process_name, button_title, window_title_contains=None, timeout=10):
    """Find a button by title in the specified process and click it."""
    script = f'''
        tell application "System Events"
            tell process "{process_name}"
                set frontmost to true
    '''
    if window_title_contains:
        script += f'set targetWindow to first window whose title contains "{window_title_contains}"\n'
    else:
        script += 'set targetWindow to window 1\n'
    script += f'''
                try
                    set theButton to first button of targetWindow whose title is "{button_title}"
                    click theButton
                    return "clicked"
                on error
                    return "not found"
                end try
            end tell
        end tell
    '''
    start = time.time()
    while time.time() - start < timeout:
        ok, out = run_applescript(script)
        if "clicked" in out:
            log_info(f"Clicked button '{button_title}' in {process_name}")
            return True
        time.sleep(1)
    log_error(f"Could not click button '{button_title}' in {process_name}")
    return False

def type_text(text):
    """Type text using keystrokes."""
    run_applescript(f'''
        tell application "System Events"
            keystroke "{text}"
        end tell
    ''')
    log_debug(f"Typed text: {text}")

def press_return():
    run_applescript('tell application "System Events" to key code 36')

def press_tab():
    run_applescript('tell application "System Events" to key code 48')

# ----------------------------------------------------------------------
# Main automation steps
# ----------------------------------------------------------------------
def main():
    log_info("=== AnyDesk Automation Started ===")
    shot("00_start.png")

    # Ensure AnyDesk is running
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(5)
    shot("01_after_launch.png")

    # Wait for main window to appear (it may show permissions status)
    if not wait_for_window("AnyDesk", "AnyDesk", timeout=30):
        log_error("AnyDesk main window did not appear. Exiting.")
        shot("01_error_no_window.png")
        sys.exit(1)

    # ---- Step 1: Grant Screen Recording permission ----
    log_info("Granting Screen Recording permission...")
    # Click the "Open Screen Recording preferences" button in AnyDesk window
    if not click_button("AnyDesk", "Open Screen Recording preferences", timeout=15):
        log_error("Could not find 'Open Screen Recording preferences' button. Trying fallback.")
        # fallback: maybe the button is called differently? Use coordinate?
        cliclick(500, 400)  # rough area where button might be
        time.sleep(3)

    # Wait for System Settings Screen Recording pane
    if not wait_for_window("System Settings", "Screen Recording", timeout=20):
        log_error("Screen Recording pane did not open.")
    shot("02_screen_recording_pane.png")

    # Click the "+" button to add an app
    if not click_button("System Settings", "+", timeout=10):
        log_error("Could not find '+' button. Using fallback coordinate.")
        cliclick(200, 300)  # typical left side
        time.sleep(2)

    # Type the path to AnyDesk.app and press Return twice
    type_text("/Applications/AnyDesk.app")
    time.sleep(2)
    press_return()
    time.sleep(2)
    press_return()
    time.sleep(3)

    # Toggle the switch (approximate position; could also use button title "AnyDesk")
    cliclick(1480, 420)   # based on your earlier script
    time.sleep(2)
    shot("03_screen_recording_toggled.png")

    # ---- Step 2: Grant Accessibility permission ----
    log_info("Granting Accessibility permission...")
    # Bring AnyDesk to front and click "Request Accessibility"
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(2)
    if not click_button("AnyDesk", "Request Accessibility", timeout=15):
        log_error("Could not find 'Request Accessibility' button. Trying fallback.")
        cliclick(500, 500)  # another rough area
        time.sleep(3)

    # Wait for Accessibility pane
    if not wait_for_window("System Settings", "Accessibility", timeout=20):
        log_error("Accessibility pane did not open.")
    shot("04_accessibility_pane.png")

    # Click "+" button
    if not click_button("System Settings", "+", timeout=10):
        cliclick(200, 300)
        time.sleep(2)

    type_text("/Applications/AnyDesk.app")
    time.sleep(2)
    press_return()
    time.sleep(2)
    press_return()
    time.sleep(3)

    # Toggle switch
    cliclick(1480, 420)
    time.sleep(2)
    shot("05_accessibility_toggled.png")

    # ---- Handle password prompt if it appears ----
    log_info("Checking for password prompt...")
    if wait_for_window("System Events", "Privacy & Security", timeout=5):
        type_text(UNATTENDED_PASSWORD)
        time.sleep(1)
        press_return()
        time.sleep(2)
        # Click "Modify Settings" if present
        click_button("System Events", "Modify Settings", timeout=3)
        shot("06_password_handled.png")

    # ---- Close AnyDesk permissions status window ----
    log_info("Closing permissions status window...")
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(3)
    # Try to click "Close" button on status window
    click_button("AnyDesk", "Close", window_title_contains="System Permissions Status", timeout=5)
    shot("07_status_closed.png")

    # ---- Set Unattended Access password (command line method) ----
    log_info("Setting Unattended Access password via command line...")
    # Ensure AnyDesk is running (daemon should be up)
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(5)

    # Run the password command as the current user (no sudo!)
    try:
        result = subprocess.run(
            [ANYDESK_BIN, "--set-password"],
            input=UNATTENDED_PASSWORD,
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode == 0:
            log_info("Unattended password set successfully via command line.")
        else:
            log_error(f"Command failed with code {result.returncode}: {result.stderr}")
            log_info("Falling back to GUI method for password.")
            # Fallback: automate settings GUI
            subprocess.run(["open", "-a", ANYDESK_APP], check=False)
            time.sleep(5)
            # Click the settings icon (e.g., three-dot menu) – coordinates may need adjustment
            cliclick(150, 50)   # top-left corner menu
            time.sleep(2)
            # Click "Settings"
            click_button("AnyDesk", "Settings", timeout=5)
            time.sleep(3)
            # Navigate to "Unattended Access" (use tab)
            for _ in range(4):
                press_tab()
                time.sleep(0.5)
            press_return()  # open section
            time.sleep(2)
            # Type password
            type_text(UNATTENDED_PASSWORD)
            time.sleep(1)
            press_return()
            log_info("Password set via GUI (hopefully).")
    except Exception as e:
        log_error(f"Exception during password setting: {e}")

    shot("08_password_set.png")

    # ---- Final: capture main AnyDesk window with ID ----
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(10)
    shot("09_final_anydesk_main.png")
    # Also capture to standard location for workflow
    subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/anydesk_final.png"], check=False)

    log_info("=== AnyDesk Automation Completed ===")
    log_info(f"Log file saved to {LOG_FILE}")
    # Copy log to debug dir for upload
    import shutil
    shutil.copy(LOG_FILE, DEBUG_DIR / "automation.log")

if __name__ == "__main__":
    main()