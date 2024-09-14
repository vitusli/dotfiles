#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

echo \$FOCUSED_WORKSPACE: $FOCUSED_WORKSPACE, \$NAME: $NAME \$1: $1 >>~/aaaa

if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
  sketchybar --animate circ 5 --set $NAME \
    \
    icon.drawing=on \
    icon.y_offset=1 \
    \
    icon.padding_left=9 \
    icon.padding_right=35 \
    icon.highlight=on \
    \
    background.drawing=on \
    background.color=0xffffffff
else
  sketchybar --animate circ 30 --set $NAME \
    \
    icon.drawing=on \
    icon.y_offset=1 \
    \
    icon.padding_left=9 \
    icon.padding_right=25 \
    icon.highlight=off \
    \
    background.drawing=on \
    background.color=0x20000000
fi

# am liebsten sowas wie:
# if $DID = 2; then
#   set "$1" = "1" on $SID = 2
# else
#   set "$1" = "1" on $SID = 1
# fi

if [ "$1" = "1" ]; then
  sketchybar --set $NAME icon="􁇲" display=2
elif [ "$1" = "2" ]; then
  sketchybar --set $NAME icon="􀈎" display=2
elif [ "$1" = "3" ]; then
  sketchybar --set $NAME icon="􀈕" display=1
elif [ "$1" = "4" ]; then
  sketchybar --set $NAME icon="􀉹" display=1
fi
