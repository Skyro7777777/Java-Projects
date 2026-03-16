#!/usr/bin/env python3
"""
RustDesk Screen Recording + Accessibility automation (Sequoia-ready)
- Ultra-aggressive bash popup killer (29+ dialogs)
- Fixed tesseract command (no more �PNG / --psm errors)
"""

import subprocess
import time
import re
import tempfile
import sys
import shutil
from pathlib import Path

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
USER_PASSWORD = "Apple@123"          # ← CHANGE THIS
MAX_WAIT = 45
SCREENSHOT_DIR = Path("/tmp")
DEBUG_DIR = SCREENSHOT_DIR / "debug_screenshots"
DEBUG_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# TOOLS
# ----------------------------------------------------------------------
TESSERACT_PATH = shutil.which("tesseract")
CLICLICK_PATH = shutil.which("cliclick")
SCREENCAPTURE_PATH = shutil.which("screencapture")

if not all([TESSERACT_PATH, CLICLICK_PATH, SCREENCAPTURE_PATH]):
    print("ERROR: Missing tesseract, cliclick or screencapture. Install with brew.")
    sys.exit(1)

# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------
def run_cmd(cmd, check=True, timeout=30, capture_output=False):
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    if capture_output:
        return result.stdout.decode('utf-8', errors='replace').strip(), result.stderr.decode('utf-8', errors='replace').strip()
    return result.returncode

def run_applescript(script):
    return subprocess.run(['osascript', '-e', script], capture_output=True, text=True).stdout.strip()

def ultra_clear_bash_dialogs():
    """SUPER aggressive dialog killer — clicks every Allow/OK in every window"""
    print("🚨 Killing ALL bash/permission dialogs (200-loop aggressive mode)...")
    apple_script = '''
    tell application "System Events"
        repeat 200 times
            set found to false
            try
                set allWindows to every window of every process
                repeat with win in allWindows
                    try
                        if (exists button "Allow" of win) then
                            click button "Allow" of win
                            set found to true
                            delay 0.3
                        end if
                        if (exists button "OK" of win) then
                            click button "OK" of win
                            set found to true
                            delay 0.3
                        end if
                        if (exists button "Continue" of win) or (exists button "Yes" of win) then
                            click button "Continue" of win
                            click button "Yes" of win
                            set found to true
                            delay 0.3
                        end if
                    end try
                end repeat
            end try
            if not found then exit repeat
            delay 0.3
        end repeat
    end tell
    '''
    run_applescript(apple_script)
    time.sleep(2)
    print("✅ Dialog killer finished.")

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
    # FIXED ORDER: options BEFORE tsv → no more --psm error
    cmd = f"{TESSERACT_PATH} {image_path} {base} --psm 6 -l eng tsv"
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
        if len(parts) >= 12 and parts[11] and int(parts[10]) > 40:
            results.append({
                'text': parts[11].strip(),
                'left': int(parts[6]), 'top': int(parts[7]),
                'width': int(parts[8]), 'height': int(parts[9])
            })
    return results

def find_text(ocr_results, targets):
    targets = [targets] if isinstance(targets, str) else targets
    for r in ocr_results:
        text = r['text'].lower()
        for t in targets:
            if t.lower() in text:
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

def wait_for_ocr(targets, timeout=MAX_WAIT, interval=2):
    start = time.time()
    while time.time() - start < timeout:
        ultra_clear_bash_dialogs()  # ← kill any new popups during wait
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

def click_all_allow_ocr():
    """Extra OCR hunter for any missed Allow buttons"""
    for _ in range(15):
        with tempfile.NamedTemporaryFile(suffix='.png', dir=SCREENSHOT_DIR, delete=False) as tmp:
            img_path = Path(tmp.name)
        take_screenshot(img_path)
        results = ocr_image(img_path)
        img_path.unlink()
        allow = find_text(results, "Allow")
        if allow:
            click_center(allow)
            time.sleep(1)
        else:
            break

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def main():
    print("=== RustDesk Permission Automation + Bash Popup Killer ===")
    ultra_clear_bash_dialogs()
    width, height = get_screen_size()
    debug_screenshot("start")

    # Step 1: Configure button in RustDesk
    print("Looking for Configure...")
    if not wait_for_ocr("Configure", 25):
        click_at(width // 2, int(height * 0.78))
    debug_screenshot("after_configure")

    # Step 2: System Settings navigation
    time.sleep(4)
    ultra_clear_bash_dialogs()
    pane = wait_for_ocr(["Screen & System Audio Recording", "Screen Recording"], 20)
    if pane:
        click_center(pane)
        time.sleep(3)
    debug_screenshot("after_pane")

    # Step 3: Toggle RustDesk
    rustdesk_row = wait_for_ocr("RustDesk", 25)
    if rustdesk_row:
        toggle_x = int(width * 0.88)
        toggle_y = rustdesk_row['top'] + rustdesk_row['height'] // 2
        click_at(toggle_x, toggle_y)
    else:
        click_at(int(width * 0.88), int(height * 0.45))
    debug_screenshot("after_toggle")

    # Step 4: Password / Unlock
    if wait_for_ocr(["Unlock to change", "Enter your password", "password"], 10):
        type_text(USER_PASSWORD)
        time.sleep(1)
        press_key("return")
        time.sleep(3)
    debug_screenshot("after_password")

    # Step 5: Quit & Reopen + final cleanup
    click_all_allow_ocr()
    if wait_for_ocr(["Quit", "Quit RustDesk"], 10):
        time.sleep(12)
    debug_screenshot("final")

    final_path = SCREENSHOT_DIR / "rustdesk_final.png"
    take_screenshot(final_path)
    print(f"✅ DONE! Final screenshot: {final_path}")
    print("Reboot + test connection.")
    print("💡 Permanent fix: Add Terminal.app to Screen & System Audio Recording manually once.")

if __name__ == "__main__":
    main()