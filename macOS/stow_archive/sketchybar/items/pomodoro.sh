source "$CONFIG_DIR/colors.sh"

sketchybar --add item pomodoro right \
  --set pomodoro \
  script="$PLUGIN_DIR/pomodoro.sh" \
  update_freq=1 \
  icon.drawing=off \
  label.padding_left=10 \
  label.padding_right=10 \
  label.y_offset=1 \
  label.font.size=12 \
  background.color=$TRANSPARENT \
  background.border_color=$WHITE \
  background.corner_radius=10 \
  background.height=17 \
  background.border_width=1
# display=1
