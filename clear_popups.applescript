-- clear_popups.applescript
-- Aggressively click common buttons on any window to clear permission popups
-- Designed to be run as the GUI user (so windows/sheets are accessible)
tell application "System Events"
  -- repeat multiple times because dialogs can reappear or be stacked
  repeat 24 times
    try
      repeat with p in (every process)
        try
          repeat with w in (every window of p)
            try
              -- common permission dialog buttons (order matters)
              if exists button "Open System Settings" of w then click button "Open System Settings" of w
              if exists button "Open System Preferences" of w then click button "Open System Preferences" of w
              if exists button "Allow" of w then click button "Allow" of w
              if exists button "Open" of w then click button "Open" of w
              if exists button "OK" of w then click button "OK" of w
              if exists button "Enable" of w then click button "Enable" of w
              if exists button "Modify Settings" of w then click button "Modify Settings" of w
            end try
          end repeat
        end try
      end repeat
    end try
    delay 0.6
  end repeat
end tell
