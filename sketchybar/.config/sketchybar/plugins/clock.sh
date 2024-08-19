#!/bin/sh

# The $NAME variable is passed from sketchybar and holds the name of
# the item invoking this script:
# https://felixkratz.github.io/SketchyBar/config/events#events-and-scripting
sketchybar --set "$NAME" icon="$(date '+%y-%m-%d')" label="$(date '+%H:%M')" \
  icon.y_offset=-1 \
  icon.padding_right=12 \
  icon.highlight=off

# not working yet
# function update {
#   sketchybar --set clock label="$(date '+%H:%M')"
# }
#
# function mouse_clicked {
#   date '+%y-%m-%d' | pbcopy
# }
#
# case "$1" in
#   "mouse.clicked") mouse_clicked
#   ;;
#   *) update
#   ;;
# esac

