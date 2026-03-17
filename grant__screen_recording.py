name: macOS GUI RustDesk - external script + click Configure

on:
  workflow_dispatch:

jobs:
  gui:
    runs-on: macos-latest
    env:
      GUI_USER: vncuser
      GUI_PASS: Apple@123
      DEBUG_DIR: /tmp/debug_screenshots
      RUSTDESK_DMG_URL: https://github.com/rustdesk/rustdesk/releases/download/1.4.6/rustdesk-1.4.6-x86_64.dmg
      SCRIPT_URL: "https://raw.githubusercontent.com/Skyro7777777/Java-Projects/refs/heads/main/grant__screen_recording.py"

    steps:

      - name: Prepare debug folder (writable)
        run: |
          mkdir -p "${DEBUG_DIR}"
          chmod 777 "${DEBUG_DIR}"

      - name: Create GUI user (vncuser) and chown debug dir
        run: |
          if ! id -u "${GUI_USER}" >/dev/null 2>&1; then
            sudo dscl . -create /Users/${GUI_USER}
            sudo dscl . -create /Users/${GUI_USER} UserShell /bin/bash
            sudo dscl . -create /Users/${GUI_USER} RealName "VNC User"
            sudo dscl . -create /Users/${GUI_USER} UniqueID "510"
            sudo dscl . -create /Users/${GUI_USER} PrimaryGroupID 20
            sudo dscl . -create /Users/${GUI_USER} NFSHomeDirectory /Users/${GUI_USER}
            sudo dscl . -passwd /Users/${GUI_USER} "${GUI_PASS}"
            sudo dscl . -append /Groups/admin GroupMembership ${GUI_USER}
            sudo createhomedir -c -u ${GUI_USER} >/dev/null 2>&1 || true
          fi
          sudo chown -R ${GUI_USER}:staff "${DEBUG_DIR}"
          chmod -R 777 "${DEBUG_DIR}"

      - name: Install optional tools (tesseract, cliclick)
        run: |
          brew install tesseract cliclick || true
          echo "tesseract: $(which tesseract || true)"
          echo "cliclick: $(which cliclick || true)"

      - name: Download & Install RustDesk
        run: |
          curl -L -o /tmp/rustdesk.dmg "${RUSTDESK_DMG_URL}"
          hdiutil attach /tmp/rustdesk.dmg -mountpoint /Volumes/RustDesk -nobrowse || true
          cp -R "/Volumes/RustDesk/RustDesk.app" /Applications/ || true
          hdiutil detach "/Volumes/RustDesk" || true
          ls -l /Applications/RustDesk.app || true

      - name: Launch RustDesk as GUI user and take initial screenshot
        run: |
          sudo -u ${GUI_USER} open -a /Applications/RustDesk.app || true
          sleep 12
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/01_after_launch.png" || true

      - name: Download your external Python automation (no inline Python)
        run: |
          if [ -z "${SCRIPT_URL}" ]; then
            echo "SCRIPT_URL empty"
            exit 1
          fi
          curl -fsSL "${SCRIPT_URL}" -o /tmp/grant__screen_recording.py
          sudo chown ${GUI_USER}:staff /tmp/grant__screen_recording.py || true
          chmod +x /tmp/grant__screen_recording.py
          echo "Downloaded external python script at /tmp/grant__screen_recording.py"

      - name: Run your Python automation as GUI user
        continue-on-error: true
        run: |
          sudo -u ${GUI_USER} env PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin" \
            python3 /tmp/grant__screen_recording.py || true
          # give macOS a moment to settle
          sleep 2
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/09_after_python.png" || true

      - name: Write AppleScript helper (click Configure) to a file
        run: |
          cat > /tmp/click_config.scpt <<'APPLESCRIPT'
-- AppleScript: find "Configure" text in RustDesk windows and click it or adjacent control
tell application "System Events"
  set procName to "RustDesk"
  repeat 6 times
    try
      if exists process procName then
        set p to process procName
        -- scan all windows
        repeat with w in (every window of p)
          try
            -- find static texts containing "configure" (case-insensitive)
            set stList to (every static text of w)
            repeat with st in stList
              try
                set stValue to (value of st) as string
                if stValue is not missing value and (stValue as string) contains "Configure" then
                  -- compute center of the static text
                  try
                    set pos to position of st
                    set sz to size of st
                    set cx to (item 1 of pos) + (item 1 of sz) / 2
                    set cy to (item 2 of pos) + (item 2 of sz) / 2
                    -- click the static text
                    tell application "System Events" to click at {cx, cy}
                    delay 0.6
                    return true
                  end try
                end if
              end try
            end repeat
            -- fallback: find any button in the window whose title contains "Configure"
            set btns to (every button of w)
            repeat with b in btns
              try
                if ((title of b) as string) contains "Configure" then
                  click b
                  delay 0.6
                  return true
                end if
              end try
            end repeat
          end try
        end repeat
      end if
    end try
    delay 0.8
  end repeat
  return false
end tell
APPLESCRIPT
          sudo chown ${GUI_USER}:staff /tmp/click_config.scpt || true
          chmod 755 /tmp/click_config.scpt || true

      - name: Run AppleScript helper as GUI user (attempt to click Configure)
        continue-on-error: true
        run: |
          # run as GUI user so Accessibility events are from the GUI session
          sudo -u ${GUI_USER} /usr/bin/osascript /tmp/click_config.scpt || true
          sleep 1
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/10_after_click_config.png" || true

      - name: Extra fallback: use cliclick to click near likely Configure areas
        run: |
          sudo -u ${GUI_USER} bash -lc '
            set -e
            for pos in "960,800" "950,780" "1000,820" "1100,400" "1000,420"; do
              IFS="," read x y <<< "$pos"
              if [ -x /usr/local/bin/cliclick ]; then
                /usr/local/bin/cliclick c:"$x,$y" || true
              elif [ -x /opt/homebrew/bin/cliclick ]; then
                /opt/homebrew/bin/cliclick c:"$x,$y" || true
              else
                osascript -e "tell application \"System Events\" to click at {$x, $y}" || true
              fi
              sleep 0.6
              /usr/sbin/screencapture -x "${DEBUG_DIR}/11_fallback_click_${x}_${y}.png" || true
            done
          '

      - name: Capture final RustDesk screenshot (for OCR & artifact)
        run: |
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x /tmp/rustdesk.png || true
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/12_final_rustdesk.png" || true
          sudo chown ${GUI_USER}:staff /tmp/rustdesk.png || true

      - name: Upload ALL screenshots artifact
        uses: actions/upload-artifact@v4
        with:
          name: all-screenshots
          path: |
            /tmp/debug_screenshots/**
            /tmp/rustdesk.png
          if-no-files-found: ignore

      - name: Short keep-alive (10 minutes)
        run: |
          echo "Finished. Sleeping 10 minutes so you can fetch artifacts."
          sleep 600