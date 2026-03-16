#!/usr/bin/env python3
"""
Automate granting Screen Recording permission to RustDesk on macOS.
Uses OCR (tesseract) to locate UI elements and cliclick to simulate clicks.
Includes debug screenshots at each step.
"""

import subprocess
import time
import re
import tempfile
import os
import sys
import shutil
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
USER_PASSWORD = "Apple@123"          # password for the user
MAX_WAIT = 30                         # seconds to wait for each step
SCREENSHOT_DIR = Path("/tmp")         # where to store temporary images
DEBUG_DIR = SCREENSHOT_DIR / "debug_screenshots"

# Create debug directory
DEBUG_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# Locate required tools
# ----------------------------------------------------------------------
TESSERACT_PATH = shutil.which("tesseract")
CLICLICK_PATH = shutil.which("cliclick")
SCREENCAPTURE_PATH = shutil.which("screencapture")

if not TESSERACT_PATH:
    print("ERROR: tesseract not found in PATH. Please install tesseract.")
    sys.exit(1)
if not CLICLICK_PATH:
    print("ERROR: cliclick not found in PATH. Please install cliclick.")
    sys.exit(1)
if not SCREENCAPTURE_PATH:
    print("ERROR: screencapture not found in PATH. This is unusual on macOS.")
    sys.exit(1)

print(f"Using tesseract: {TESSERACT_PATH}")
print(f"Using cliclick: {CLICLICK_PATH}")
print(f"Using screencapture: {SCREENCAPTURE_PATH}")

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def run_cmd(cmd, check=True, timeout=30, capture_output=False):
    """
    Run a shell command. If capture_output=True, return (stdout, stderr) as strings
    with errors replaced. Otherwise just return the return code (or raise).
    """
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, timeout=timeout)
    if check and result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        print(f"Command failed: {cmd}\nstderr: {err}")
        raise RuntimeError(f"Command failed: {cmd}")
    if capture_output:
        out = result.stdout.decode('utf-8', errors='replace').strip()
        err = result.stderr.decode('utf-8', errors='replace').strip()
        return out, err
    return result.returncode

def get_screen_size():
    """Return (width, height) of main display using system_profiler."""
    output, _ = run_cmd("system_profiler SPDisplaysDataType | grep Resolution", capture_output=True, check=False)
    match = re.search(r'(\d+) x (\d+)', output)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1920, 1080

def take_screenshot(path):
    """Take a screenshot of the entire screen using full path."""
    run_cmd(f"{SCREENCAPTURE_PATH} -x {path}")

def debug_screenshot(name):
    """Save a screenshot with a timestamp for debugging."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = DEBUG_DIR / f"{name}_{timestamp}.png"
    take_screenshot(path)
    print(f"Debug screenshot saved: {path}")

def ocr_image(image_path):
    """
    Run tesseract on image, return list of dicts with text, bbox.
    Uses tesseract TSV output.
    """
    base = image_path.with_suffix('')
    tsv_path = base.with_suffix('.tsv')
    cmd = f"{TESSERACT_PATH} {image_path} {base} tsv"
    stdout, stderr = run_cmd(cmd, check=False, capture_output=True)
    if not tsv_path.exists():
        print(f"Tesseract failed to create TSV. stderr: {stderr}")
        if stdout:
            print(f"stdout: {stdout}")
        return []
    with open(tsv_path) as f:
        lines = f.readlines()
    tsv_path.unlink()

    results = []
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < 12:
            continue
        if parts[11] and int(parts[10]) > 30:
            results.append({
                'text': parts[11],
                'left': int(parts[6]),
                'top': int(parts[7]),
                'width': int(parts[8]),
                'height': int(parts[9])
            })
    return results

def find_text(ocr_results, target, case_sensitive=False):
    target_lower = target.lower() if not case_sensitive else target
    for r in ocr_results:
        text = r['text'] if case_sensitive else r['text'].lower()
        if (case_sensitive and target in text) or (not case_sensitive and target_lower in text):
            return r
    return None

def click_at(x, y):
    run_cmd(f"{CLICLICK_PATH} c:{x},{y}")

def click_center(ocr_result):
    x = ocr_result['left'] + ocr_result['width'] // 2
    y = ocr_result['top'] + ocr_result['height'] // 2
    click_at(x, y)
    time.sleep(1)

def type_text(text):
    run_cmd(f"{CLICLICK_PATH} t:{text}")

def press_key(key):
    run_cmd(f"{CLICLICK_PATH} kp:{key}")

def wait_for_ocr(target, timeout=MAX_WAIT, interval=2):
    start = time.time()
    while time.time() - start < timeout:
        with tempfile.NamedTemporaryFile(suffix='.png', dir=SCREENSHOT_DIR, delete=False) as tmp:
            img_path = Path(tmp.name)
        take_screenshot(img_path)
        results = ocr_image(img_path)
        img_path.unlink()
        found = find_text(results, target)
        if found:
            return found
        time.sleep(interval)
    return None

def wait_and_click(target, timeout=MAX_WAIT):
    found = wait_for_ocr(target, timeout)
    if found:
        click_center(found)
        return True
    return False

# ----------------------------------------------------------------------
# Main automation steps
# ----------------------------------------------------------------------
def main():
    print("Starting Screen Recording permission automation...")
    width, height = get_screen_size()
    print(f"Screen resolution: {width}x{height}")
    debug_screenshot("initial_state")

    # Step 1: Wait for RustDesk main window and click "Configure"
    print("Looking for 'Configure' button...")
    if not wait_and_click("Configure", timeout=20):
        # Improved fallback: bottom center (960, 810 on 1920x1080)
        print("OCR failed, using fallback coordinate for Configure.")
        click_at(width // 2, int(height * 0.75))
        time.sleep(2)
        debug_screenshot("after_configure_fallback")

    # Step 2: System dialog: click "Open System Settings"
    print("Looking for 'Open System Settings'...")
    if not wait_and_click("Open System Settings", timeout=15):
        print("Fallback: clicking left-center for Open System Settings.")
        click_at(width // 2 - 200, height // 2)  # ~760,540
        time.sleep(2)
        debug_screenshot("after_open_sys_settings_fallback")

    # Step 3: In System Settings, find RustDesk row and enable switch
    print("Waiting for System Settings to open...")
    time.sleep(5)
    debug_screenshot("system_settings_opened")

    rustdesk_ocr = wait_for_ocr("RustDesk", timeout=20)
    if rustdesk_ocr:
        switch_x = rustdesk_ocr['left'] + rustdesk_ocr['width'] + 100
        switch_y = rustdesk_ocr['top'] + rustdesk_ocr['height'] // 2
        print(f"Clicking switch at ({switch_x}, {switch_y})")
        click_at(switch_x, switch_y)
        time.sleep(2)
        debug_screenshot("after_switch_ocr")
    else:
        print("RustDesk text not found, using fallback switch location.")
        click_at(int(width * 0.8), int(height * 0.4))  # ~1536,432
        time.sleep(2)
        debug_screenshot("after_switch_fallback")

    # Step 4: If password prompt appears, enter password
    print("Checking for password prompt...")
    if wait_for_ocr("Enter your password", timeout=5):
        print("Password prompt detected, typing password...")
        type_text(USER_PASSWORD)
        time.sleep(1)
        press_key("return")
        time.sleep(2)
        debug_screenshot("after_password_entry")
        wait_and_click("Modify Settings", timeout=5)

    # Step 5: Handle "Quit & Reopen" dialog
    print("Looking for 'Quit' button in RustDesk...")
    if wait_and_click("Quit", timeout=10):
        print("RustDesk quitting, waiting for restart...")
        time.sleep(10)
        debug_screenshot("after_quit")
    else:
        pass

    # Step 6: Wait for RustDesk to be back and take final screenshot
    print("Waiting for RustDesk to restart...")
    time.sleep(10)
    final_screenshot = SCREENSHOT_DIR / "rustdesk_screen.png"
    take_screenshot(final_screenshot)
    print(f"Final screenshot saved to {final_screenshot}")
    debug_screenshot("final_state")

    print("Automation completed.")

if __name__ == "__main__":
    main()