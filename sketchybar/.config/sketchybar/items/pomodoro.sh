source "$CONFIG_DIR/colors.sh"

sketchybar --add item pomodoro right \
  --set pomodoro \
  script="$PLUGIN_DIR/pomodoro.sh" \
  update_freq=1 \
  icon.drawing=off \
  label.padding_left=10 \
  label.padding_right=10 \
  border_width= 1 \
  background.drawing=on \
  background.height= 6 \
  background.color=0x10000000 \
  background.corner_radius=12
# display=1
