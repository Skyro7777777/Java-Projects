-- grant_screen_recording.applescript
-- Automates granting Screen Recording permission to RustDesk on macOS
-- Run with: osascript grant_screen_recording.applescript

-- Configuration
property passwordStr : "Apple@123"
property timeoutSec : 30
property shortDelay : 1
property mediumDelay : 2
property longDelay : 5

-- Helper: wait for a window with title containing text
on waitForWindow(processName, windowText, maxWait)
    set startTime to current date
    repeat while (current date) - startTime < maxWait
        tell application "System Events"
            if exists (process processName) then
                tell process processName
                    if exists (first window whose title contains windowText) then return true
                end tell
            end if
        end tell
        delay 0.5
    end repeat
    return false
end waitForWindow

-- Helper: click a button by its title in a window (optionally within a specific process)
on clickButton(processName, windowTitle, buttonTitle, maxWait)
    set startTime to current date
    repeat while (current date) - startTime < maxWait
        tell application "System Events"
            if processName is not "" and not (exists process processName) then
                delay 0.5
            else
                tell process processName
                    if exists (first window whose title contains windowTitle) then
                        set targetWindow to first window whose title contains windowTitle
                        if exists (first button of targetWindow whose title contains buttonTitle) then
                            click (first button of targetWindow whose title contains buttonTitle)
                            return true
                        end if
                    end if
                end tell
            end if
        end tell
        delay 0.5
    end repeat
    return false
end clickButton

-- Helper: click a UI element by description or index fallback
on clickUIElement(processName, elementDesc, elementType, instance)
    tell application "System Events"
        tell process processName
            set uiElements to UI elements whose description contains elementDesc
            if (count uiElements) > 0 then
                click item instance of uiElements
                return true
            end if
        end tell
    end tell
    return false
end clickUIElement

-- Main routine
on run
    try
        -- Step 1: Wait for RustDesk main window and click "Configure" button
        log "Waiting for RustDesk main window..."
        if not waitForWindow("RustDesk", "RustDesk", timeoutSec) then
            error "RustDesk main window not found"
        end if
        
        tell application "System Events"
            tell process "RustDesk"
                set frontmost to true
                delay shortDelay
                -- Try to click button with title "Configure"
                if exists (first button whose title is "Configure") then
                    click (first button whose title is "Configure")
                    log "Clicked Configure button"
                else
                    -- Fallback: click at approximate position (using cliclick)
                    do shell script "sudo -u vncuser cliclick c:200,300"
                    log "Fallback: cliclick at (200,300)"
                end if
            end tell
        end tell
        
        -- Step 2: Wait for system permission dialog and click "Open System Settings"
        delay longDelay
        log "Waiting for Screen Recording permission dialog..."
        if clickButton("System Events", "Screen Recording", "Open System Settings", timeoutSec) then
            log "Clicked Open System Settings"
        else
            -- Fallback: try clicking center of screen (assuming dialog is frontmost)
            do shell script "sudo -u vncuser cliclick c:512,384"
            delay mediumDelay
        end if
        
        -- Step 3: Wait for System Settings to open and navigate to Screen Recording pane
        delay longDelay
        log "Waiting for System Settings to open..."
        if not waitForWindow("System Settings", "Screen Recording", timeoutSec) then
            -- If not found, try opening directly via URL
            do shell script "open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenRecording'"
            delay longDelay
        end if
        
        tell application "System Events"
            tell process "System Settings"
                set frontmost to true
                delay mediumDelay
                
                -- Step 4: Unlock if necessary (lock button present and disabled checkboxes)
                try
                    set lockButton to first button whose description contains "lock"
                    if exists lockButton then
                        click lockButton
                        delay mediumDelay
                        keystroke passwordStr
                        delay shortDelay
                        keystroke return
                        delay longDelay
                        log "Unlocked settings"
                    end if
                end try
                
                -- Step 5: Find RustDesk row and enable its switch
                set found to false
                try
                    -- Look for table in the main window
                    set mainTable to table 1 of scroll area 1 of window 1
                    repeat with aRow in (every row of mainTable)
                        try
                            if value of static text 1 of aRow is "RustDesk" then
                                -- Click the checkbox (switch) in that row
                                click checkbox 1 of aRow
                                set found to true
                                log "Enabled RustDesk in Screen Recording list"
                                exit repeat
                            end if
                        end on error
                    end repeat
                on error errMsg
                    log "Error finding table: " & errMsg
                end try
                
                if not found then
                    -- Fallback: try clicking at typical switch location (right side, mid)
                    do shell script "sudo -u vncuser cliclick c:700,300"
                    log "Fallback: cliclick at (700,300) to toggle switch"
                end if
            end tell
        end tell
        
        -- Step 6: Handle password prompt for modifying settings (if appears)
        delay longDelay
        log "Checking for password confirmation dialog..."
        tell application "System Events"
            set pwDialogFound to false
            repeat with proc in {"System Settings", "SecurityAgent"}
                if exists (process proc) then
                    tell process proc
                        if exists (first window whose title contains "Privacy & Security" and description contains "password") then
                            set pwWindow to first window whose title contains "Privacy & Security"
                            set frontmost to true
                            keystroke passwordStr
                            delay shortDelay
                            try
                                click (first button of pwWindow whose title is "Modify Settings")
                            on error
                                keystroke return
                            end try
                            set pwDialogFound to true
                            log "Entered password and confirmed"
                            exit repeat
                        end if
                    end tell
                end if
            end repeat
            if not pwDialogFound then
                log "No password prompt appeared (might have been already unlocked)"
            end if
        end tell
        
        -- Step 7: Handle "Quit & Reopen" dialog from RustDesk
        delay longDelay
        log "Waiting for RustDesk restart dialog..."
        if clickButton("RustDesk", "RustDesk", "Quit", 15) then
            log "Clicked Quit to restart RustDesk"
        else
            -- Try clicking any button with "Quit" in it
            tell application "System Events"
                tell process "RustDesk"
                    try
                        set quitButton to first button whose title contains "Quit"
                        click quitButton
                        log "Fallback: clicked Quit button"
                    end try
                end tell
            end tell
        end if
        
        -- Step 8: Wait for RustDesk to restart and come to foreground
        delay longDelay * 2
        log "Waiting for RustDesk to restart..."
        if waitForWindow("RustDesk", "RustDesk", timeoutSec) then
            tell application "System Events" to tell process "RustDesk" to set frontmost to true
            log "RustDesk restarted successfully"
        else
            error "RustDesk did not restart"
        end if
        
        -- Step 9: Take a screenshot (optional, for OCR)
        delay mediumDelay
        do shell script "sudo -u vncuser screencapture -x /tmp/rustdesk_screen_final.png"
        log "Screenshot saved to /tmp/rustdesk_screen_final.png"
        
        return "Screen Recording permission granted successfully."
        
    on error errMsg
        log "Error: " & errMsg
        return "Failed: " & errMsg
    end try
end run
