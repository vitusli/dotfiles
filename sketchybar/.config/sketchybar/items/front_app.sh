#!/bin/bash

front_app=(
  icon.font="sketchybar-app-font:Regular:16.0"
  icon.background.drawing=on
  icon.padding_left=12
  label.padding_right=12
  background.padding_left=15
  background.color=0x30d5d5d5
  background.corner_radius=25
  display=active
  script="$PLUGIN_DIR/front_app.sh"
  click_script="open -a 'Mission Control'"
)

sketchybar --add item front_app left \
  --set front_app "${front_app[@]}" \
  --subscribe front_app front_app_switched
