#!/bin/bash

SPACE_SIDS=(1 2 3 4 5 6 7 8 9 10)

for sid in "${SPACE_SIDS[@]}"; do
  sketchybar --add space space.$sid left \
    --set space.$sid space=$sid \
    icon=$sid \
    label.font="sketchybar-app-font:Regular:16.0" \
    label.padding_right=20 \
    label.y_offset=-1 \
    script="$PLUGIN_DIR/ms_space.sh"
done

# Here is the icon for the active app indicator, used to be a chevron, future vitus says that makes no sense
# here the app per space is rendered
sketchybar --add item space_separator left \
  --set space_separator icon="􀯿" \
  icon.padding_left=3 \
  icon.drawing=off \
  label.drawing=off \
  background.drawing=off \
  script="$PLUGIN_DIR/ms_space_windows.sh" \
  --subscribe space_separator space_windows_change

# if [ $SELECTED = true ]; then
#   sketchybar --set $NAME background.drawing=on icon.highlight=off background.color=0x40000000
# else
#   sketchybar --set $NAME background.drawing=on icon.highlight=on background.color=0x20000000
#
# fi

