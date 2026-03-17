#!/usr/bin/env python3
"""
AnyDesk Automation – Grants Screen Recording & Accessibility permissions,
handles intermediate dialogs, and sets Unattended Access password.
All steps are logged and debug screenshots are saved.
"""

import subprocess
import time
import pathlib
import sys
import os
import logging
import shutil
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

console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logger.addHandler(console)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_info(msg): logger.info(msg)
def log_error(msg): logger.error(msg)
def log_debug(msg): logger.debug(msg)

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

def run_applescript(script, max_retries=2):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(['osascript', '-e', script],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True, result.stdout.strip()
            log_debug(f"AppleScript attempt {attempt+1} failed: {result.stderr}")
            if attempt < max_retries - 1:
                time.sleep(2)
        except subprocess.TimeoutExpired:
            log_error("AppleScript timed out")
            if attempt < max_retries - 1:
                time.sleep(2)
    return False, ""

def cliclick(x, y):
    try:
        subprocess.run([CLICLICK, f"c:{x},{y}"], check=True, timeout=8)
        log_debug(f"cliclick at ({x},{y})")
    except Exception:
        log_debug(f"cliclick failed, trying AppleScript click at ({x},{y})")
        run_applescript(f'tell application "System Events" to click at {{{x},{y}}}')

def wait_for_window(process_name, window_title_contains, timeout=20):
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

def click_button_by_title(process_name, button_title, window_title_contains=None, timeout=10):
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

def click_button_containing(process_name, button_text, window_title_contains=None, timeout=10):
    """Click a button whose title contains the given text."""
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
                    set theButton to first button of targetWindow whose title contains "{button_text}"
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
            log_info(f"Clicked button containing '{button_text}' in {process_name}")
            return True
        time.sleep(1)
    log_error(f"Could not click button containing '{button_text}' in {process_name}")
    return False

def type_text(text):
    run_applescript(f'tell application "System Events" to keystroke "{text}"')
    log_debug(f"Typed text: {text}")

def press_return():
    run_applescript('tell application "System Events" to key code 36')

def press_tab():
    run_applescript('tell application "System Events" to key code 48')

def grant_permission(permission_name, button_text, settings_pane_title):
    """
    Generic function to grant a permission.
    - Click the button in AnyDesk (e.g., "Open Screen Recording preferences")
    - Wait for System Settings pane
    - Add AnyDesk via "+" and typing path
    - Toggle the switch
    """
    log_info(f"Granting {permission_name} permission...")
    if not click_button_containing("AnyDesk", button_text, timeout=15):
        log_error(f"Could not find '{button_text}' button. Trying fallback coordinate.")
        cliclick(500, 400)  # fallback
        time.sleep(3)

    # If a dialog with "Open System Settings" appears, click it
    if wait_for_window("System Events", "would like to", timeout=5):
        log_info("Dialog appeared, clicking 'Open System Settings'")
        click_button_by_title("System Events", "Open System Settings", timeout=5)
        time.sleep(3)

    if not wait_for_window("System Settings", settings_pane_title, timeout=20):
        log_error(f"{settings_pane_title} pane did not open.")
    shot(f"02_{permission_name}_pane.png")

    # Click the "+" button
    if not click_button_by_title("System Settings", "+", timeout=10):
        log_error("Could not find '+' button. Using fallback coordinate.")
        cliclick(200, 300)
        time.sleep(2)

    # Type app path
    type_text("/Applications/AnyDesk.app")
    time.sleep(2)
    press_return()
    time.sleep(2)
    press_return()
    time.sleep(3)

    # Toggle the switch (approximate position; can be refined)
    cliclick(1480, 420)
    time.sleep(2)
    shot(f"03_{permission_name}_toggled.png")

    # Handle password prompt if it appears
    if wait_for_window("System Events", "Privacy & Security", timeout=5):
        log_info("Password prompt detected.")
        type_text(UNATTENDED_PASSWORD)
        time.sleep(1)
        press_return()
        time.sleep(2)
        click_button_by_title("System Events", "Modify Settings", timeout=3)
        shot("04_password_handled.png")

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

    # Wait for main window to appear
    if not wait_for_window("AnyDesk", "AnyDesk", timeout=30):
        log_error("AnyDesk main window did not appear. Exiting.")
        shot("01_error_no_window.png")
        sys.exit(1)

    # Step 1: Screen Recording
    grant_permission("ScreenRecording", "Open Screen Recording preferences", "Screen Recording")

    # Step 2: Accessibility
    grant_permission("Accessibility", "Request Accessibility", "Accessibility")

    # Close any remaining permission status window
    log_info("Closing AnyDesk permissions status window...")
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(3)
    click_button_by_title("AnyDesk", "Close", window_title_contains="System Permissions Status", timeout=5)
    shot("05_status_closed.png")

    # Step 3: Set Unattended Access password (command line method)
    log_info("Setting Unattended Access password via command line...")
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(5)

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
            log_error(f"Command failed: {result.stderr}")
            # Fallback: GUI automation for settings
            log_info("Falling back to GUI password setting.")
            subprocess.run(["open", "-a", ANYDESK_APP], check=False)
            time.sleep(5)
            # Click settings icon (three-dot menu) - adjust coordinates if needed
            cliclick(150, 50)
            time.sleep(2)
            click_button_containing("AnyDesk", "Settings", timeout=5)
            time.sleep(3)
            # Navigate to Unattended Access (tab several times)
            for _ in range(4):
                press_tab()
                time.sleep(0.5)
            press_return()
            time.sleep(2)
            type_text(UNATTENDED_PASSWORD)
            time.sleep(1)
            press_return()
            log_info("Password set via GUI (hopefully).")
    except Exception as e:
        log_error(f"Exception during password setting: {e}")

    shot("06_password_set.png")

    # Final: capture main AnyDesk window with ID
    subprocess.run(["open", "-a", ANYDESK_APP], check=False)
    time.sleep(10)
    shot("07_final_anydesk_main.png")
    # Also capture to standard location
    subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/anydesk_final.png"], check=False)

    log_info("=== AnyDesk Automation Completed ===")
    log_info(f"Log file saved to {LOG_FILE}")
    shutil.copy(LOG_FILE, DEBUG_DIR / "automation.log")

if __name__ == "__main__":
    main()