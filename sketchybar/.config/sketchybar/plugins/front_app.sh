#!/bin/sh

mine
if [ "$SENDER" = "front_app_switched" ]; then
  sketchybar --set "$NAME" label.drawing=on \
    label="$INFO" \
    icon="$($CONFIG_DIR/plugins/icon_map_fn.sh "$INFO")"
fi

#Image of the app
# if [ "$SENDER" = "front_app_switched" ]; then
#   sketchybar --set "$NAME" label="$INFO" icon.background.image="app.$INFO" icon.background.image.scale=0.7 label.drawing=off
#
#   apps=$AEROSPACE_LIST_OF_WINDOWS_IN_FOCUSED_MONITOR
#   icon_strip=" "
#   if [ "${apps}" != "" ]; then
#     while read -r app
#     do
#       icon_strip+=" $($CONFIG_DIR/plugins/icon_map_fn.sh "$app")"
#     done <<< "${apps}"
#   else
#     icon_strip=" —"
#   fi
#   sketchybar --set space.$AEROSPACE_FOCUSED_MONITOR_NO label="$icon_strip"
# fi
