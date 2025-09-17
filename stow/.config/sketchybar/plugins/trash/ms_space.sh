#!/bin/bash

update() {
  WIDTH="dynamic"
  if [ "$SELECTED" = "true" ]; then
    WIDTH="140"
  fi
# previously: icon.highlight=$SELECTED, now icon.highlight=on/off
  sketchybar --animate tanh 8 --set $NAME label.width=$WIDTH 
}

if [ $SELECTED = true ]; then
  sketchybar --set $NAME background.drawing=on icon.highlight=off background.color=0x70000000 
else
  sketchybar --set $NAME background.drawing=on icon.highlight=on background.color=0x20000000 

fi

case "$SENDER" in
  "mouse.clicked") mouse_clicked
  ;;
  *) update
  ;;
esac

