#Requires AutoHotkey v2.0.2
#SingleInstance Force
FancyWM(action) {
    RunWait(format("fancywm.exe --action {}", action), , "Hide")
}

; ctrl-alt-cmd-h/j/k/l = Focus
^!#h::FancyWM("MoveFocusLeft")
^!#j::FancyWM("MoveFocusDown")
^!#k::FancyWM("MoveFocusUp")
^!#l::FancyWM("MoveFocusRight")

; ctrl-alt-cmd-shift-h/j/k/l = Move window
^!#+h::FancyWM("MoveLeft")
^!#+j::FancyWM("MoveDown")
^!#+k::FancyWM("MoveUp")
^!#+l::FancyWM("MoveRight")

; ctrl-alt-cmd-i/o = Prev/Next desktop
^!#i::FancyWM("SwitchToLeftDesktop")
^!#o::FancyWM("SwitchToRightDesktop")

; ctrl-alt-cmd-1/2 = Move window to desktop 1/2 and follow
^!#1::{
    FancyWM("MoveToDesktop1")
    FancyWM("SwitchToDesktop1")
}
^!#2::{
    FancyWM("MoveToDesktop2")
    FancyWM("SwitchToDesktop2")
}

; ctrl-alt-cmd-space = Toggle stack panel (accordion)
^!#Space::FancyWM("CreateStackPanel")
