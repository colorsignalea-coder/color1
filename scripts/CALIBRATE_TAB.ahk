#NoEnv
#SingleInstance Force
SetTitleMatchMode, 2
CoordMode, Mouse, Window

iniFile := A_WorkingDir . "\configs\current_config.ini"

MsgBox, 64, Calibration Start, 1. Open your MT4 Terminal.`n2. Ensure the "Tester" panel is visible at the bottom.`n3. Click OK to start calibration.

WinActivate, MetaTrader 4
WinWaitActive, MetaTrader 4,, 5
if (ErrorLevel) {
    MsgBox, 16, Error, MT4 Window not found!
    ExitApp
}

WinGetPos, wx, wy, ww, wh, A
IniRead, relx11, %iniFile%, coords, relx_report, 0.259
IniRead, rely11, %iniFile%, coords, rely_report, 0.940

curX := Round(relx11 * ww)
curY := Round(rely11 * wh)

MouseMove, %curX%, %curY%
MsgBox, 36, check, Is the mouse cursor currently on the "Report" (or "Graph") tab?`n`nIf YES, press Yes.`nIf NO, press No to re-calibrate.

ifMsgBox, Yes
{
    MsgBox, 64, Done, Coordinates look good. No changes made.
    ExitApp
}

MsgBox, 64, Re-Calibrate, Move your mouse over the center of the "Report" tab button and RIGHT CLICK.
KeyWait, RButton, D
MouseGetPos, nX, nY
KeyWait, RButton, U

newRelX := nX / ww
newRelY := nY / wh

IniWrite, %newRelX%, %iniFile%, coords, relx_report
IniWrite, %newRelY%, %iniFile%, coords, rely_report

MsgBox, 64, Saved, New coordinates saved!`nRelX: %newRelX%`nRelY: %newRelY%`n`nTry running the script again.
