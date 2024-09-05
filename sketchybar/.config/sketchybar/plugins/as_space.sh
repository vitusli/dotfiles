#!/usr/bin/env bash

echo \$FOCUSED_WORKSPACE: $FOCUSED_WORKSPACE, \$NAME: $NAME \$1: $1 >>~/aaaa

if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
  sketchybar --set $NAME background.drawing=on icon.highlight=off background.color=0x70000000 background.width=200
else
  sketchybar --set $NAME background.drawing=on icon.highlight=on background.color=0x20000000
fi
