name: macOS GUI AnyDesk – Grant Permissions + Unattended Access

on: workflow_dispatch

jobs:
  gui:
    runs-on: macos-latest
    env:
      GUI_USER: vncuser
      GUI_PASS: Apple@123
      DEBUG_DIR: /tmp/debug_screenshots
      ANYDESK_DMG_URL: "https://download.anydesk.com/anydesk.dmg"
      SCRIPT_URL: "https://raw.githubusercontent.com/Skyro7777777/Java-Projects/refs/heads/main/grant__screen_recording.py"
      UNATTENDED_PASSWORD: "Apple@123"

    steps:
      - name: Prepare debug folder
        run: |
          mkdir -p "${DEBUG_DIR}"
          chmod 777 "${DEBUG_DIR}"

      - name: Create GUI user (vncuser)
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

      - name: Install Homebrew tools (tesseract, cliclick)
        run: |
          brew install tesseract cliclick || true
          echo "TESSERACT: $(which tesseract || true)"
          echo "CLICLICK: $(which cliclick || true)"

      - name: Download & Install AnyDesk (portable DMG)
        run: |
          set -euxo pipefail
          curl -L -o /tmp/anydesk.dmg "${ANYDESK_DMG_URL}"
          hdiutil attach /tmp/anydesk.dmg -mountpoint /Volumes/AnyDesk -nobrowse || true
          cp -R "/Volumes/AnyDesk/AnyDesk.app" /Applications/ || true
          hdiutil detach "/Volumes/AnyDesk" || true
          ls -l /Applications/AnyDesk.app || true

      - name: Reset TCC + launch AnyDesk
        run: |
          sudo -u ${GUI_USER} tccutil reset ScreenCapture com.anydesk.AnyDesk || true
          sudo -u ${GUI_USER} tccutil reset Accessibility com.anydesk.AnyDesk || true
          sudo -u ${GUI_USER} open -a "/Applications/AnyDesk.app" || true
          sleep 20
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/01_after_launch.png" || true

      - name: Run automation script (permissions + add to both panes)
        run: |
          set -euxo pipefail
          if [ -z "${SCRIPT_URL}" ]; then
            echo "SCRIPT_URL not set"; exit 1
          fi
          curl -fsSL "${SCRIPT_URL}" -o /tmp/grant_screen_recording.py
          sudo chown ${GUI_USER}:staff /tmp/grant_screen_recording.py || true
          sudo chmod +x /tmp/grant_screen_recording.py || true
          sudo -u ${GUI_USER} env PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin" python3 /tmp/grant_screen_recording.py || true
          sleep 15
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/09_after_script.png" || true

      - name: Enable Unattended Access (robust service start + set password)
        run: |
          set -euxo pipefail

          GUI_USER="${GUI_USER:-vncuser}"
          UNATTENDED_PASSWORD="${UNATTENDED_PASSWORD:-Apple@123}"
          DEBUG_DIR="${DEBUG_DIR:-/tmp/debug_screenshots}"

          # Try to find the AnyDesk binary - prefer expected path, otherwise find first executable in Contents/MacOS
          AD_BIN="/Applications/AnyDesk.app/Contents/MacOS/AnyDesk"
          if [ ! -x "${AD_BIN}" ]; then
            # try alternative names in that folder
            for f in /Applications/AnyDesk.app/Contents/MacOS/*; do
              if [ -x "$f" ]; then
                AD_BIN="$f"
                break
              fi
            done
          fi

          echo "[anydesk] Binary resolved to: ${AD_BIN}"
          if [ ! -x "${AD_BIN}" ]; then
            echo "ERROR: AnyDesk binary not found or not executable at expected path. Listing /Applications:"
            ls -l /Applications || true
            exit 1
          fi

          SERVICE_LOG="/tmp/anydesk_service.log"
          # stop any existing AnyDesk instances
          pkill -f AnyDesk || true
          sleep 2

          echo "[anydesk] starting AnyDesk service as root..."
          sudo env PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin" "${AD_BIN}" --service > "${SERVICE_LOG}" 2>&1 &

          # wait for service readiness
          echo "[anydesk] waiting for service to respond..."
          READY=0
          for i in $(seq 1 30); do
            sleep 1
            if sudo "${AD_BIN}" --get-id >/tmp/anydesk_id.out 2>/tmp/anydesk_err.out; then
              echo "[anydesk] service responsive (iteration ${i})"
              READY=1
              break
            fi
          done

          if [ "${READY}" -ne 1 ]; then
            echo "[anydesk] service did not become responsive in time. Collecting diagnostics..."
            ps auxww | egrep "AnyDesk|anydesk" || true
            tail -n 200 "${SERVICE_LOG}" || true
            cat /tmp/anydesk_err.out || true
            # continue to attempt set-password once anyway
          fi

          echo "[anydesk] attempting to set unattended password (retries)..."
          SET_OK=0
          for j in $(seq 1 6); do
            echo "[anydesk] set-password attempt ${j}"
            if echo "${UNATTENDED_PASSWORD}" | sudo "${AD_BIN}" --set-password >/tmp/anydesk_setpw_out 2>/tmp/anydesk_setpw_err; then
              echo "[anydesk] password set (attempt ${j})"
              SET_OK=1
              break
            else
              echo "[anydesk] set-password failed (attempt ${j})"
              sleep 2
            fi
          done

          if [ "${SET_OK}" -ne 1 ]; then
            echo "[anydesk] FAILED to set unattended password — saving diagnostics"
            ps auxww | egrep "AnyDesk|anydesk" || true
            tail -n 200 "${SERVICE_LOG}" || true
            echo "--- /tmp/anydesk_setpw_err ---"
            cat /tmp/anydesk_setpw_err || true
            echo "--- /tmp/anydesk_setpw_out ---"
            cat /tmp/anydesk_setpw_out || true
          fi

          # screenshots & copy logs to debug dir (artifact)
          sudo -u "${GUI_USER}" /usr/sbin/screencapture -x "${DEBUG_DIR}/12_unattended_enabled.png" || true
          cp -f "${SERVICE_LOG}" "${DEBUG_DIR}/anydesk_service.log" || true
          cp -f /tmp/anydesk_id.out "${DEBUG_DIR}/anydesk_id.out" || true
          cp -f /tmp/anydesk_err.out "${DEBUG_DIR}/anydesk_err.out" || true
          cp -f /tmp/anydesk_setpw_err "${DEBUG_DIR}/anydesk_setpw_err" || true
          cp -f /tmp/anydesk_setpw_out "${DEBUG_DIR}/anydesk_setpw_out" || true

      - name: Final cleanup + screenshot
        run: |
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x /tmp/anydesk_final.png || true
          sudo chown ${GUI_USER}:staff /tmp/anydesk_final.png || true
          sudo -u ${GUI_USER} /usr/sbin/screencapture -x "${DEBUG_DIR}/11_final_anydesk.png" || true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: all-screenshots
          path: |
            /tmp/debug_screenshots/**
            /tmp/anydesk_final.png
            /tmp/anydesk_service.log
            /tmp/anydesk_id.out
            /tmp/anydesk_err.out
            /tmp/anydesk_setpw_err
            /tmp/anydesk_setpw_out
          if-no-files-found: ignore

      - name: Keep runner alive
        run: |
          echo "Runner will remain alive for 6 hours so you can fetch artifacts and connect if needed."
          for i in {1..6}; do sleep 3600; done