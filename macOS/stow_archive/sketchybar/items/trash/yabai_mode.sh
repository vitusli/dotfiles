#!/bin/bash

sketchybar    --add item yabai_mode right \
              --set yabai_mode script="$PLUGIN_DIR/yabai_mode.sh" \
              --set yabai_mode click_script="$PLUGIN_DIR/yabai_mode_click.sh" \
              --subscribe yabai_mode space_change

