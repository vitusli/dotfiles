mouse_entered() {
  sketchybar --set test label="erfolgreich"
}

mouse_exited() {
  sketchybar --set test label=""
}

case "$SENDER" in
"mouse.entered")
  mouse_entered
  ;;
"mouse.exited")
  mouse_exited
  ;;
*)
  update
  ;;
esac
