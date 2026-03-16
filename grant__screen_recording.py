#!/usr/bin/env python3
"""
Automate granting Screen Recording permission to RustDesk on macOS.
Uses OCR (tesseract) to locate UI elements and cliclick to simulate clicks.
This version uses absolute paths for external tools and handles binary output.
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
        # If capture_output is True, we have bytes; try to decode for error message
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
    output, _ = run_cmd("system_profiler SPDisplaysDataType | grep Resolution", capture_output=True)
    match = re.search(r'(\d+) x (\d+)', output)
    if match:
        return int(match.group(1)), int(match.group(2))
    # fallback if resolution not found (common on headless runners)
    return 1920, 1080

def take_screenshot(path):
    """Take a screenshot of the entire screen using full path."""
    run_cmd(f"{SCREENCAPTURE_PATH} -x {path}")

def ocr_image(image_path):
    """
    Run tesseract on image, return list of dicts with text, bbox.
    Uses tesseract TSV output.
    """
    base = image_path.with_suffix('')
    tsv_path = base.with_suffix('.tsv')
    # Run tesseract, do not capture stdout (TSV is written to file), capture stderr for debugging.
    cmd = f"{TESSERACT_PATH} {image_path} {base} tsv"
    stdout, stderr = run_cmd(cmd, check=False, capture_output=True)
    if not tsv_path.exists():
        print(f"Tesseract failed to create TSV. stderr: {stderr}")
        if stdout:
            print(f"stdout: {stdout}")
        return []
    with open(tsv_path) as f:
        lines = f.readlines()
    tsv_path.unlink()  # clean up

    # Parse TSV: level,page_num,block_num,par_num,line_num,word_num,left,top,width,height,conf,text
    results = []
    for line in lines[1:]:  # skip header
        parts = line.strip().split('\t')
        if len(parts) < 12:
            continue
        if parts[11] and int(parts[10]) > 30:  # confidence > 30
            results.append({
                'text': parts[11],
                'left': int(parts[6]),
                'top': int(parts[7]),
                'width': int(parts[8]),
                'height': int(parts[9])
            })
    return results

def find_text(ocr_results, target, case_sensitive=False):
    """Return first result whose text contains target (case‑insensitive by default)."""
    target_lower = target.lower() if not case_sensitive else target
    for r in ocr_results:
        text = r['text'] if case_sensitive else r['text'].lower()
        if (case_sensitive and target in text) or (not case_sensitive and target_lower in text):
            return r
    return None

def click_at(x, y):
    """Click at screen coordinates using cliclick."""
    run_cmd(f"{CLICLICK_PATH} c:{x},{y}")

def click_center(ocr_result):
    """Click at the center of an OCR bounding box."""
    x = ocr_result['left'] + ocr_result['width'] // 2
    y = ocr_result['top'] + ocr_result['height'] // 2
    click_at(x, y)
    time.sleep(1)

def type_text(text):
    """Type text using cliclick (must have focus)."""
    run_cmd(f"{CLICLICK_PATH} t:{text}")

def press_key(key):
    """Press a special key (return, tab, space) using cliclick."""
    run_cmd(f"{CLICLICK_PATH} kp:{key}")

def wait_for_ocr(target, timeout=MAX_WAIT, interval=2):
    """Keep taking screenshots until target text appears, return OCR result."""
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
    """Wait for target text, then click its center. Return True if successful."""
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

    # Step 1: Wait for RustDesk main window and click "Configure"
    print("Looking for 'Configure' button...")
    if not wait_and_click("Configure", timeout=20):
        # Fallback: try clicking near bottom of screen (common RustDesk position)
        print("OCR failed, using fallback coordinate for Configure.")
        click_at(width // 2, int(height * 0.7))
        time.sleep(2)

    # Step 2: System dialog: click "Open System Settings"
    print("Looking for 'Open System Settings'...")
    if not wait_and_click("Open System Settings", timeout=15):
        print("Fallback: clicking center of screen.")
        click_at(width // 2, height // 2)
        time.sleep(2)

    # Step 3: In System Settings, find RustDesk row and enable switch
    print("Waiting for System Settings to open...")
    time.sleep(5)

    # Look for "RustDesk" text in the table
    rustdesk_ocr = wait_for_ocr("RustDesk", timeout=20)
    if rustdesk_ocr:
        # Click to the right of the text where the switch should be
        switch_x = rustdesk_ocr['left'] + rustdesk_ocr['width'] + 100
        switch_y = rustdesk_ocr['top'] + rustdesk_ocr['height'] // 2
        print(f"Clicking switch at ({switch_x}, {switch_y})")
        click_at(switch_x, switch_y)
        time.sleep(2)
    else:
        # Fallback: try clicking where switch often is (right side, mid)
        print("RustDesk text not found, using fallback switch location.")
        click_at(int(width * 0.8), int(height * 0.4))
        time.sleep(2)

    # Step 4: If password prompt appears, enter password
    print("Checking for password prompt...")
    if wait_for_ocr("Enter your password", timeout=5):
        print("Password prompt detected, typing password...")
        type_text(USER_PASSWORD)
        time.sleep(1)
        press_key("return")
        time.sleep(2)
        # Click "Modify Settings" if present
        wait_and_click("Modify Settings", timeout=5)

    # Step 5: Handle "Quit & Reopen" dialog
    print("Looking for 'Quit' button in RustDesk...")
    if wait_and_click("Quit", timeout=10):
        print("RustDesk quitting, waiting for restart...")
        time.sleep(10)
    else:
        # Maybe already restarted?
        pass

    # Step 6: Wait for RustDesk to be back and take final screenshot
    print("Waiting for RustDesk to restart...")
    time.sleep(10)
    screenshot_path = SCREENSHOT_DIR / "rustdesk_screen.png"
    take_screenshot(screenshot_path)
    print(f"Final screenshot saved to {screenshot_path}")

    print("Automation completed.")

if __name__ == "__main__":
    main()