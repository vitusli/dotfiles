# keyd - Linux Keyboard Remapper

Native Linux solution. Simple config, runs as systemd service.

## Installation

```bash
# Ubuntu/Debian
sudo apt install keyd

# Or from source
git clone https://github.com/rvaiya/keyd
cd keyd
make && sudo make install
```

## Setup

```bash
# Copy config
sudo cp ~/.config/keyd/default.conf /etc/keyd/default.conf

# Start service
sudo systemctl enable --now keyd

# Reload after config changes
sudo keyd reload
```

## Test

```bash
# Interactive key tester
sudo keyd monitor
```

## Features

| Shortcut | Action |
|----------|--------|
| Caps Lock (hold) | Hyperkey (Ctrl+Alt+Super) |
| Caps Lock (tap) | Escape |
| Escape (hold) | FN layer |
| FN + hjkl | Arrow keys |
| Alt + h/l | Word left/right |
| Alt + u/o/a/s | ü/ö/ä/ß |
| Alt+Shift + u/o/a/s | Ü/Ö/Ä/ẞ |

## Docs

- https://github.com/rvaiya/keyd
- `man keyd`
