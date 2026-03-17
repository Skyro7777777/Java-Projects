-- dump_rustdesk_ui.scpt
-- Enumerate RustDesk windows, static text, buttons, groups; write to /tmp/rustdesk_ui.txt
tell application "System Events"
  set outLines to {}
  if not (exists process "RustDesk") then
    do shell script "printf %s " & quoted form of "NO_PROCESS" & " > /tmp/rustdesk_ui.txt"
    return
  end if
  set p to process "RustDesk"
  set push to my pushLine
  repeat with w in (every window of p)
    try
      set wname to name of w
    on error
      set wname to "<unnamed>"
    end try
    set end of outLines to "WINDOW: " & wname
    try
      set wb to position of w
      set ws to size of w
      set end of outLines to "  WINDOW_POS: " & (wb as string) & " SIZE: " & (ws as string)
    end try

    -- static texts
    try
      repeat with t in (every static text of w)
        try
          set v to value of t
        on error
          set v to "<no value>"
        end try
        try
          set pos to position of t
          set sz to size of t
          set end of outLines to "  STATIC: " & (v as string) & " | POS:" & (pos as string) & " SIZE:" & (sz as string)
        on error
          set end of outLines to "  STATIC: " & (v as string)
        end try
      end repeat
    end try

    -- buttons
    try
      repeat with b in (every button of w)
        try
          set btitle to title of b
        on error
          try
            set btitle to name of b
          on error
            set btitle to "<no-title>"
          end try
        end try
        try
          set posb to position of b
          set szb to size of b
          set end of outLines to "  BUTTON: " & (btitle as string) & " | POS:" & (posb as string) & " SIZE:" & (szb as string)
        on error
          set end of outLines to "  BUTTON: " & (btitle as string)
        end try
      end repeat
    end try

    -- groups (collect static text inside groups)
    try
      repeat with g in (every group of w)
        set end of outLines to "  GROUP:"
        try
          repeat with gt in (every static text of g)
            try
              set end of outLines to "    GROUP_STATIC: " & (value of gt as string)
            end try
          end repeat
        end try
      end repeat
    end try

  end repeat

  -- write lines to file
  set joined to ""
  repeat with L in outLines
    set joined to joined & L & linefeed
  end repeat
  do shell script "printf %s " & quoted form of joined & " > /tmp/rustdesk_ui.txt"
end tell

on pushLine(s)
  -- helper, unused (keeps compatibility)
  return
end pushLine
