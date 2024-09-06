#!/usr/bin/env bash

echo \$FOCUSED_WORKSPACE: $FOCUSED_WORKSPACE, \$NAME: $NAME \$1: $1 >>~/aaaa

if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
  sketchybar --set $NAME \
    \
    icon.drawing=on \
    icon="􀍡" \
    icon.y_offset=1 \
    \
    icon.padding_left=9 \
    icon.padding_right=25 \
    icon.highlight=on \
    \
    background.drawing=on \
    background.color=0xffffffff
else
  sketchybar --set $NAME \
    \
    icon.drawing=on \
    icon="􀀀" \
    icon.y_offset=1 \
    \
    icon.padding_left=9 \
    icon.padding_right=25 \
    icon.highlight=off \
    \
    background.drawing=on \
    background.color=0x20000000
fi
