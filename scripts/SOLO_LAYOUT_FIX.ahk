#NoEnv
#SingleInstance Force
SetWorkingDir, %A_ScriptDir%

; =====================================================
; SOLO Report Layout Fixer (v1.2) - English UI
; =====================================================

global CSS_TAG := "<style type='text/css'>/* Layout Fix v5.3 EN */ body { overflow-x: auto !important; margin: 0 !important; padding: 10px !important; } table { width: 100PERCENT !important; table-layout: fixed !important; } tr > td:first-child { width: 220px !important; min-width: 220px !important; white-space: nowrap !important; background: #f8f9fa !important; font-weight: bold; vertical-align: top; border-right: 2px solid #ddd !important; }</style>"
StringReplace, CSS_TAG, CSS_TAG, PERCENT, `%, All

; Initial Startup Message (Auto-close after 3s)
MsgBox, 64, SOLO LAYOUT FIXER, [F11] - Manual Fix All Reports`nReal-time automatic layout fix is active., 3

return

F11::
    ; Try reading reportRoot from config.ini
    IniRead, reportRoot, configs\current_config.ini, folders, report_base_path, C:\2026NEWOPTMIZER
    if (reportRoot = "ERROR")
        reportRoot := "C:\2026NEWOPTMIZER"
        
    MsgBox, 4, SOLO LAYOUT FIXER, Start scanning with root: %reportRoot%?`n(Includes D:\ drive and subfolders automatically), 10
    IfMsgBox, No
        return
    
    count := 0
    Loop, %reportRoot%\*.htm, 0, 1
    {
        filePath := A_LoopFileFullPath
        FileRead, txt, %filePath%
        if (ErrorLevel || InStr(txt, "Layout Fix v5.3"))
            continue
            
        newTxt := ""
        StringReplace, newTxt, txt, </head>, %CSS_TAG%</head>, All
        if (newTxt == txt)
            StringReplace, newTxt, txt, </HEAD>, %CSS_TAG%</HEAD>, All
            
        if (newTxt != txt) {
            FileDelete, %filePath%
            FileAppend, %newTxt%, %filePath%, UTF-8
            count++
        }
    }
    
    ; Also scan D:\ drive as fallback if different from reportRoot
    if (reportRoot != "D:\2026NEWOPTMIZER" && FileExist("D:\2026NEWOPTMIZER")) {
        Loop, D:\2026NEWOPTMIZER\*.htm, 0, 1
        {
            filePath := A_LoopFileFullPath
            FileRead, txt, %filePath%
            if (ErrorLevel || InStr(txt, "Layout Fix v5.3"))
                continue
            newTxt := ""
            StringReplace, newTxt, txt, </head>, %CSS_TAG%</head>, All
            if (newTxt == txt) StringReplace, newTxt, txt, </HEAD>, %CSS_TAG%</HEAD>, All
            if (newTxt != txt) {
                FileDelete, %filePath%
                FileAppend, %newTxt%, %filePath%, UTF-8
                count++
            }
        }
    }
    
    MsgBox, 64, DONE, Fixed %count% report(s) successfully!, 3
return
