#!/usr/bin/env python3
import subprocess, time, pathlib

DEBUG = pathlib.Path("/tmp/debug_screenshots")
DEBUG.mkdir(parents=True, exist_ok=True)

TESSERACT = "/opt/homebrew/bin/tesseract"
CLICLICK  = "/opt/homebrew/bin/cliclick"
MAGICK    = "/opt/homebrew/bin/magick"   # FIXED: ImageMagick 7 uses magick, not convert

clicker_proc = None

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def start_allow_clicker():
    global clicker_proc
    script = '''repeat
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
        delay 0.5
    end repeat'''
    clicker_proc = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("Background Allow clicker started")

def stop_allow_clicker():
    if clicker_proc: clicker_proc.terminate()

def shot(name):
    subprocess.run(["/usr/sbin/screencapture", "-x", str(DEBUG / name)], check=False)
    log(f"Screenshot: {name}")

def applescript(code):
    r = subprocess.run(['osascript', '-e', code], capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip()

def cliclick(x, y):
    subprocess.run([CLICLICK, f"c:{x},{y}"], timeout=8, check=False)
    log(f"Clicked ({x},{y})")

def activate_rustdesk():
    applescript('tell application "RustDesk" to activate')
    time.sleep(2)

def preprocess(img_path):
    pre = img_path.with_name(img_path.stem + "_pre.png")
    subprocess.run([MAGICK, str(img_path),
                    "-colorspace", "Gray", "-normalize",
                    "-contrast-stretch", "3%", "-sharpen", "0x1.5",
                    "-threshold", "58%", str(pre)], check=False)
    return pre if pre.exists() else img_path

def find_text_ocr(target):
    shot("ocr_search.png")
    tmp = DEBUG / "ocr_tmp.png"
    subprocess.run(["/usr/sbin/screencapture", "-x", str(tmp)], check=False)
    pre = preprocess(tmp)
    base = pre.with_suffix('')
    subprocess.run([TESSERACT, str(pre), str(base), "--psm", "7", "tsv"], check=False, timeout=15)
    tsv = base.with_suffix('.tsv')
    if not tsv.exists(): return None
    with open(tsv, errors="ignore") as f:
        lines = f.readlines()
    tsv.unlink(missing_ok=True); tmp.unlink(missing_ok=True); pre.unlink(missing_ok=True)
    target = target.lower()
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < 12: continue
        if parts[11] and int(parts[10]) > 25 and target in parts[11].lower():
            x = int(parts[6]) + int(parts[8])//2
            y = int(parts[7]) + int(parts[9])//2
            log(f"OCR found '{target}' at ({x},{y})")
            return (x, y)
    log(f"OCR missed '{target}'")
    return None

def click_configure():
    log("=== Clicking Configure ===")
    activate_rustdesk()
    methods = [
        ("OCR Configure", lambda: find_text_ocr("Configure")),
        ("OCR Permissions", lambda: find_text_ocr("Permissions")),  # click slightly below
        ("Fallback 960,650", lambda: (960,650)),
        ("Fallback 960,700", lambda: (960,700)),
        ("Fallback 960,720", lambda: (960,720)),
        ("Fallback 980,680", lambda: (980,680)),
    ]
    for name, func in methods:
        log(f"Trying: {name}")
        pos = func()
        if pos:
            x, y = pos
            if name == "OCR Permissions": y += 80  # click below the text
            cliclick(x, y)
            time.sleep(4)
            # Check if dialog appeared
            ok, out = applescript('tell application "System Events" to if exists (first window whose title contains "Screen Recording") then return "yes" else return "no"')
            if "yes" in out.lower():
                log("SUCCESS: Screen Recording dialog opened!")
                shot("02_configure_success.png")
                return True
    log("All attempts failed → opening settings directly")
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"])
    time.sleep(6)
    shot("02_configure_fallback.png")
    return False

def toggle_or_add_rustdesk():
    log("Toggling or adding RustDesk in settings...")
    time.sleep(4)
    pos = find_text_ocr("RustDesk")
    if pos:
        cliclick(pos[0] + 220, pos[1])  # toggle switch
        log("Toggled RustDesk")
    else:
        log("RustDesk not in list → trying + button add")
        cliclick(1350, 280)  # + button position in Sequoia pane
        time.sleep(2)
        cliclick(800, 400)   # approximate "RustDesk" in the add dialog
        time.sleep(2)
        cliclick(1100, 550)  # Add button
    time.sleep(3)
    shot("04_after_toggle_or_add.png")

# ==================== MAIN ====================
log("=== RustDesk Screen Recording Automation v2 (fixed for Sequoia) ===")
shot("00_start.png")
start_allow_clicker()

# Trigger initial bash permission
subprocess.run(["/usr/sbin/screencapture", "-x", "/tmp/dummy.png"])
time.sleep(4)
shot("01_after_bash.png")

click_configure()
toggle_or_add_rustdesk()

# Password & quit/reopen
applescript('tell application "System Events" to if exists (button "Modify Settings" of window 1) then keystroke "Apple@123" & key code 36')
time.sleep(3)
applescript('tell application "RustDesk" to quit')
time.sleep(4)
applescript('tell application "RustDesk" to activate')
time.sleep(8)
shot("07_final.png")

stop_allow_clicker()
log("=== Done ===")