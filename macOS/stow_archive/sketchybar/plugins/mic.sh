#!/bin/bash

source "$CONFIG_DIR/colors.sh"

MIC_VOLUME=$(osascript -e 'input volume of (get volume settings)')

if [[ $MIC_VOLUME -eq 0 ]]; then
  sketchybar --animate circ 20 \
    --set mic icon=􀊳 \
    icon.color=$RED \
    label="muted" \
    label.color=$RED
elif [[ $MIC_VOLUME -gt 0 ]]; then
  sketchybar --animate circ 20 \
    --set mic icon=􀊱 \
    label="" \
    icon.color=$WHITE
fi

#todo on click / hover start timer
