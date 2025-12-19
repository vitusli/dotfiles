#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

echo \$FOCUSED_WORKSPACE: $FOCUSED_WORKSPACE, \$NAME: $NAME \$1: $1 >>~/.dotfiles/sketchybar/.config/sketchybar/plugins

if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
  sketchybar --animate circ 5 --set $NAME \
    \
    icon.drawing=on \
    icon.y_offset=1 \
    icon.font.size=16 \
    \
    icon.padding_left=13 \
    icon.padding_right=0 \
    icon.highlight=on \
    \
    background.drawing=on \
    background.height=11 \
    background.color=0xffffffff
else
  sketchybar --animate circ 30 --set $NAME \
    \
    icon.drawing=on \
    icon.y_offset=1 \
    icon.font.size=1 \
    \
    icon.padding_left=0 \
    icon.padding_right=0 \
    icon.highlight=off \
    \
    background.drawing=on \
    background.height=10 \
    background.color=0x20000000
fi

# if [ "$1" = "1" ]; then
#   sketchybar --set $NAME icon="􁇲" display=1
# elif [ "$1" = "2" ]; then
#   sketchybar --set $NAME icon="􀈎" display=1
# elif [ "$1" = "3" ]; then
#   sketchybar --set $NAME icon="􀉹" display=1
# fi
