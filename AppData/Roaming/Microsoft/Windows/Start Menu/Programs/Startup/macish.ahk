#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode("Input")

FancyWM(action) {
    RunWait(format("fancywm.exe --action {}", action), , "Hide")
}

;; Disable Language Switching
#Space::Return

;;LWin::LCtrl
;;LCtrl::LWin
;;RWin::RCtrl
;;RCtrl::RWin

;; ======= Caps Lock Remapping =======
;; deactivate capslock completely
SetCapsLockState("AlwaysOff")
CapsLock::Return  ; Block CapsLock key completely

;; ======= Special Character Shortcuts =======
; öüäß keys - Variables to track key presses
global AltU_Pressed := false
global AltA_Pressed := false
global AltO_Pressed := false
global AltS_Pressed := false

!u:: {  ; Alt + u
    global AltU_Pressed := true
    SetTimer(ResetAltU, -1000)  ; Set a timer to reset the variable after 1 second
    Send("ü")  ; Send the 'ü' character
}

!a:: {  ; Alt + a
    global AltA_Pressed := true
    SetTimer(ResetAltA, -1000)
    Send("ä")
}

!o:: {  ; Alt + o
    global AltO_Pressed := true
    SetTimer(ResetAltO, -1000)
    Send("ö")
}

!s:: {  ; Alt + s
    global AltS_Pressed := true
    SetTimer(ResetAltS, -1000)
    Send("ß")
}

; Alt + Shift for uppercase ÜÖÄẞ
+!u::Send("Ü")  ; Alt + Shift + u
+!a::Send("Ä")  ; Alt + Shift + a
+!o::Send("Ö")  ; Alt + Shift + o
+!s::Send("ẞ")  ; Alt + Shift + s

;; ======= Text Editing Shortcuts =======
; Alt + Backspace: Lösche ein Wort
!Backspace:: {
    Send("^+{Left}")  ; Markiere das vorherige Wort
    Send("{Del}")     ; Lösche die Markierung
}

; Ctrl + Backspace: Lösche die gesamte Zeile
^Backspace:: {
    Send("{Home}")    ; Bewege den Cursor an den Anfang der Zeile
    Send("+{Down}")   ; Markiere die gesamte Zeile (inklusive Zeilenumbruch)
    Send("{Del}")     ; Lösche die Markierung
}

; Alt + h: Ctrl + Left (ein Wort nach links)
!h::Send("^{Left}")

; Alt + l: Ctrl + Right (ein Wort nach rechts)
!l::Send("^{Right}")

; Alt + Shift + h: Ctrl + Shift + Left (markiere ein Wort nach links)
+!h::Send("^+{Left}")

; Alt + Shift + l: Ctrl + Shift + Right (markiere ein Wort nach rechts)
+!l::Send("^+{Right}")

;; ======= Reset Timer Functions =======
ResetAltU() {
    global AltU_Pressed := false
}
ResetAltA() {
    global AltA_Pressed := false
}
ResetAltO() {
    global AltO_Pressed := false
}
ResetAltS() {
    global AltS_Pressed := false
}

;; ======= FancyWM Window Management =======
; Block Live Captions shortcut (Win+Ctrl+L)
#^l::Return

; Move focus (Win+Alt+Ctrl+H/J/K/L)
#!^h::FancyWM("MoveFocusLeft")
#!^j::FancyWM("MoveFocusDown")
#!^k::FancyWM("MoveFocusUp")
#!^l::FancyWM("MoveFocusRight")

; Move window (Ctrl+Shift+H/J/K/L)
^+h::FancyWM("MoveLeft")
^+j::FancyWM("MoveDown")
^+k::FancyWM("MoveUp")
^+l::FancyWM("MoveRight")

; Swap window (Win+Alt+Ctrl+Shift+H/J/K/L)
#!^+h::FancyWM("SwapLeft")
#!^+j::FancyWM("SwapDown")
#!^+k::FancyWM("SwapUp")
#!^+l::FancyWM("SwapRight")

; Panel management
#!^Space::FancyWM("CreateStackPanel")
#!^+Space::FancyWM("PullWindowUp")
#!^w::FancyWM("ToggleFloatingMode")
#!^v::FancyWM("CreateVerticalPanel")
#!^b::FancyWM("CreateHorizontalPanel")

; Resize (Win+Alt+Ctrl+Plus/Minus)
#!^=::FancyWM("IncreaseWidth")
#!^-::FancyWM("DecreaseWidth")
#!^+=::FancyWM("IncreaseHeight")
#!^+-::FancyWM("DecreaseHeight")

; Desktop switching (Win+Alt+Ctrl+I/O)
#!^i::FancyWM("SwitchToLeftDesktop")
#!^o::FancyWM("SwitchToRightDesktop")
#!^d::FancyWM("SwitchToPreviousDesktop")

; Move window to desktop
#!^1::FancyWM("MoveToDesktop1")
#!^2::FancyWM("MoveToDesktop2")
