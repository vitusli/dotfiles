SendMode Input

;;LWin::LCtrl
;;LCtrl::LWin
;;RWin::RCtrl
;;RCtrl::RWin

;; ======= Caps Lock Remapping =======
;; deactivate capslock completely
SetCapsLockState, AlwaysOff
CapsLock::return  ; Block CapsLock key completely

;; ======= Special Character Shortcuts =======
;öüäß keys, Variables to track key presses
global AltU_Pressed := false
global AltA_Pressed := false
global AltO_Pressed := false
global AltS_Pressed := false

!u::  ; Alt + u
    AltU_Pressed := true
    SetTimer, ResetAltU, -1000  ; Set a timer to reset the variable after 1 second
    Send, {ASC 0252}  ; Send the 'ü' character immediately
    return

!a::  ; Alt + a
    AltA_Pressed := true
    SetTimer, ResetAltA, -1000  ; Set a timer to reset the variable after 1 second
    Send, {ASC 0228}  ; Send the 'ä' character immediately
    return

!o::  ; Alt + o
    AltO_Pressed := true
    SetTimer, ResetAltO, -1000  ; Set a timer to reset the variable after 1 second
    Send, {ASC 0246}  ; Send the 'ö' character immediately
    return

!s::  ; Alt + s
    AltS_Pressed := true
    SetTimer, ResetAltS, -1000  ; Set a timer to reset the variable after 1 second
    Send, {U+00DF}  ; Send the 'ß' character using its Unicode value
    return

; Alt + Shift for uppercase ÜÖÄẞ
+!u::  ; Alt + Shift + u
    Send, {ASC 0220}  ; Send the 'Ü' character
    return

+!a::  ; Alt + Shift + a
    Send, {ASC 0196}  ; Send the 'Ä' character
    return

+!o::  ; Alt + Shift + o
    Send, {ASC 0214}  ; Send the 'Ö' character
    return

+!s::  ; Alt + Shift + s
    Send, {U+1E9E}  ; Send the 'ẞ' character
    return

;; ======= Text Editing Shortcuts =======
; Alt + Backspace: Lösche ein Wort
!Backspace::
    Send, ^+{Left}  ; Markiere das vorherige Wort
    Send, {Del}     ; Lösche die Markierung
    return

; Ctrl + Backspace: Lösche die gesamte Zeile
^Backspace::
    Send, {Home}    ; Bewege den Cursor an den Anfang der Zeile
    Send, +{Down}   ; Markiere die gesamte Zeile (inklusive Zeilenumbruch)
    Send, {Del}     ; Lösche die Markierung
    return

; Alt + h: Ctrl + Left (ein Wort nach links)
!h::
    Send, ^{Left}
    return

; Alt + l: Ctrl + Right (ein Wort nach rechts)
!l::
    Send, ^{Right}
    return

; Alt + Shift + h: Ctrl + Shift + Left (markiere ein Wort nach links)
+!h::
    Send, ^+{Left}
    return

; Alt + Shift + l: Ctrl + Shift + Right (markiere ein Wort nach rechts)
+!l::
    Send, ^+{Right}
    return

;; ======= Reset Timers =======
ResetAltU:
    AltU_Pressed := false
    return
ResetAltA:
    AltA_Pressed := false
    return
ResetAltO:
    AltO_Pressed := false
    return
ResetAltS:
    AltS_Pressed := false
    return

