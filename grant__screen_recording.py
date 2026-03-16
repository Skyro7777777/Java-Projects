#!/usr/bin/env python3
"""
Fixed & robust automation for RustDesk Screen Recording permission on macOS (Sonoma/Sequoia+).
Uses updated OCR targets from real 2025–2026 UI + sidebar navigation.
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
USER_PASSWORD = "Apple@123"          # ← CHANGE THIS
MAX_WAIT = 45                        # increased for Sequoia loading
SCREENSHOT_DIR = Path("/tmp")
DEBUG_DIR = SCREENSHOT_DIR / "debug_screenshots"
DEBUG_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------
TESSERACT_PATH = shutil.which("tesseract")
CLICLICK_PATH = shutil.which("cliclick")
SCREENCAPTURE_PATH = shutil.which("screencapture")

if not all([TESSERACT_PATH, CLICLICK_PATH, SCREENCAPTURE_PATH]):
    print("ERROR: Missing tesseract, cliclick or screencapture.")
    sys.exit(1)

# ----------------------------------------------------------------------
# Helpers (improved OCR)
# ----------------------------------------------------------------------
def run_cmd(cmd, check=True, timeout=30, capture_output=False):
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    if capture_output:
        return result.stdout.decode('utf-8', errors='replace').strip(), result.stderr.decode('utf-8', errors='replace').strip()
    return result.returncode

def get_screen_size():
    out, _ = run_cmd("system_profiler SPDisplaysDataType | grep Resolution", capture_output=True, check=False)
    match = re.search(r'(\d+) x (\d+)', out)
    return (int(match.group(1)), int(match.group(2))) if match else (1920, 1080)

def take_screenshot(path):
    run_cmd(f"{SCREENCAPTURE_PATH} -x {path}")

def debug_screenshot(name):
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = DEBUG_DIR / f"{name}_{ts}.png"
    take_screenshot(path)
    print(f"Debug: {path}")

def ocr_image(image_path):
    base = image_path.with_suffix('')
    cmd = f"{TESSERACT_PATH} {image_path} {base} tsv --psm 6 -l eng"  # ← improved for UI text
    run_cmd(cmd, check=False)
    tsv_path = base.with_suffix('.tsv')
    if not tsv_path.exists():
        return []
    with open(tsv_path) as f:
        lines = f.readlines()
    tsv_path.unlink()
    results = []
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 12 and parts[11] and int(parts[10]) > 40:  # higher confidence
            results.append({
                'text': parts[11].strip(),
                'left': int(parts[6]), 'top': int(parts[7]),
                'width': int(parts[8]), 'height': int(parts[9])
            })
    return results

def find_text(ocr_results, targets, case_sensitive=False):
    targets = [targets] if isinstance(targets, str) else targets
    for r in ocr_results:
        text = r['text'] if case_sensitive else r['text'].lower()
        for t in targets:
            t = t if case_sensitive else t.lower()
            if t in text:
                return r
    return None

def click_at(x, y):
    run_cmd(f"{CLICLICK_PATH} c:{x},{y}")

def click_center(ocr_result):
    x = ocr_result['left'] + ocr_result['width'] // 2
    y = ocr_result['top'] + ocr_result['height'] // 2
    click_at(x, y)
    time.sleep(1.5)

def type_text(text):
    run_cmd(f"{CLICLICK_PATH} t:{text}")

def press_key(key):
    run_cmd(f"{CLICLICK_PATH} kp:{key}")

def wait_for_ocr(targets, timeout=MAX_WAIT, interval=2):
    start = time.time()
    while time.time() - start < timeout:
        with tempfile.NamedTemporaryFile(suffix='.png', dir=SCREENSHOT_DIR, delete=False) as tmp:
            img_path = Path(tmp.name)
        take_screenshot(img_path)
        results = ocr_image(img_path)
        img_path.unlink()
        found = find_text(results, targets)
        if found:
            return found
        time.sleep(interval)
    return None

def wait_and_click(targets, timeout=MAX_WAIT):
    found = wait_for_ocr(targets, timeout)
    if found:
        click_center(found)
        return True
    return False

# ----------------------------------------------------------------------
# Main (fixed flow)
# ----------------------------------------------------------------------
def main():
    print("=== RustDesk Screen Recording Automation (Sequoia-ready) ===")
    width, height = get_screen_size()
    debug_screenshot("start")

    # Step 1: Click "Configure" in RustDesk sidebar (confirmed 2025–2026)
    print("Waiting for RustDesk 'Configure' button...")
    if not wait_and_click("Configure", 25):
        print("Fallback: center-bottom click for Configure")
        click_at(width // 2, int(height * 0.78))
    debug_screenshot("after_configure")

    # Step 2: Wait for System Settings + navigate to correct pane
    print("Waiting for System Settings...")
    time.sleep(4)
    debug_screenshot("settings_opened")

    # NEW: Navigate sidebar if needed (critical fix for Sequoia)
    print("Looking for Screen & System Audio Recording pane...")
    pane = wait_for_ocr(["Screen & System Audio Recording", "Screen Recording"], timeout=20)
    if pane:
        print("Navigating to Screen & System Audio Recording pane...")
        click_center(pane)
        time.sleep(3)
    debug_screenshot("after_pane_navigation")

    # Step 3: Find RustDesk row and toggle ON
    print("Looking for RustDesk in permission list...")
    rustdesk_row = wait_for_ocr("RustDesk", timeout=25)
    if rustdesk_row:
        # Toggle is far right of the row (dynamic)
        toggle_x = int(width * 0.88)  # reliable right-column position
        toggle_y = rustdesk_row['top'] + rustdesk_row['height'] // 2
        print(f"Clicking toggle at ({toggle_x}, {toggle_y})")
        click_at(toggle_x, toggle_y)
        time.sleep(2)
    else:
        # Ultimate fallback
        print("Fallback toggle click")
        click_at(int(width * 0.88), int(height * 0.45))
    debug_screenshot("after_toggle")

    # Step 4: Handle unlock/password (updated phrases)
    print("Checking for password prompt...")
    if wait_for_ocr(["Unlock to change", "Enter your password", "password"], timeout=8):
        print("Unlock detected – entering password")
        type_text(USER_PASSWORD)
        time.sleep(1)
        press_key("return")
        time.sleep(3)
    debug_screenshot("after_password")

    # Step 5: Quit & Reopen if RustDesk asks
    if wait_and_click(["Quit", "Quit RustDesk", "Reopen"], 10):
        print("RustDesk quitting...")
        time.sleep(12)
    debug_screenshot("after_quit")

    # Final
    final_path = SCREENSHOT_DIR / "rustdesk_final.png"
    take_screenshot(final_path)
    print(f"✅ Automation finished! Screenshot: {final_path}")
    print("Reboot recommended + test connection.")

if __name__ == "__main__":
    main()