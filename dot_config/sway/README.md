# Sway Konfiguration (AeroSpace-Äquivalent für Wayland)

Diese Sway-Konfiguration ist eine Übersetzung der AeroSpace-Konfiguration von macOS für Linux/Wayland.

## Warum Sway statt i3?

- **Wayland-nativ** – moderner, sicherer, bessere Performance
- **Fast 1:1 kompatibel mit i3-Configs**
- **Compositor eingebaut** – kein picom nötig
- **Bessere HiDPI/Multi-Monitor Unterstützung**
- **Touchpad-Gesten nativ**

## Installation auf Ubuntu

### 1. Sway und Abhängigkeiten installieren

```bash
# Sway und Basis-Tools
sudo apt update
sudo apt install sway swaylock swayidle swaybg

# Statusbar
sudo apt install waybar

# App-Launcher (wie Spotlight)
sudo apt install wofi

# Benachrichtigungen (Wayland-nativ, statt dunst)
sudo apt install mako-notifier

# Screenshot-Tool
sudo apt install grim slurp

# Clipboard
sudo apt install wl-clipboard

# Screen Sharing (für Zoom, Teams, etc.)
sudo apt install xdg-desktop-portal-wlr
```

### Alle Pakete auf einmal:

```bash
sudo apt install sway swaylock swayidle swaybg waybar wofi mako-notifier grim slurp wl-clipboard xdg-desktop-portal-wlr
```

## Abhängigkeiten-Übersicht

| Paket | Beschreibung | AeroSpace-Äquivalent |
|-------|--------------|----------------------|
| **sway** | Tiling Window Manager | AeroSpace selbst |
| **swaylock** | Bildschirmsperre | macOS Lock Screen |
| **swayidle** | Idle-Management | macOS Sleep |
| **waybar** | Statusbar | macOS Menubar |
| **wofi** | App-Launcher | Spotlight |
| **mako-notifier** | Benachrichtigungen | macOS Notifications |
| **grim + slurp** | Screenshots | Cmd+Shift+4 |
| **wl-clipboard** | Clipboard | macOS Clipboard |

## Setup

### 1. Config anwenden (mit chezmoi)

```bash
chezmoi apply
```

### 2. Oder manuell kopieren

```bash
mkdir -p ~/.config/sway
cp dot_config/sway/config ~/.config/sway/config
```

### 3. Monitor-Namen herausfinden

```bash
swaymsg -t get_outputs
```

Dann in der Config anpassen:
```
workspace 1 output <DEIN_HAUPTMONITOR>
workspace 2 output <DEIN_ZWEITMONITOR>
```

### 4. Sway starten

Beim Login-Screen "Sway" als Session wählen, oder:

```bash
# Von TTY aus starten
sway
```

## Tastenkürzel-Übersicht

| Tastenkombination | Aktion |
|-------------------|--------|
| `Ctrl+Alt+Super+h/j/k/l` | Fokus wechseln |
| `Ctrl+Alt+Super+Shift+h/j/k/l` | Fenster verschieben |
| `Ctrl+Alt+Super+Space` | Layout: stacked ↔ split |
| `Ctrl+Alt+Super+Shift+Space` | Layout: horizontal ↔ vertikal |
| `Ctrl+Alt+Super+w` | Floating toggle |
| `Ctrl+Alt+Super+d` | Workspace back-and-forth |
| `Ctrl+Alt+Super+1/2` | Fenster zu Workspace 1/2 |
| `Ctrl+Alt+Super+minus/equal` | Resize |
| `Ctrl+Alt+Super+/` | Service-Modus |

### Service-Modus

| Taste | Aktion |
|-------|--------|
| `r` | Config neu laden |
| `q` | Sway beenden |
| `e` | Layout zurücksetzen |
| `f` | Floating toggle |
| `Backspace` | Andere Fenster schließen |
| `Escape` | Service-Modus verlassen |

## Unterschiede zu AeroSpace

| AeroSpace Feature | Sway Status |
|-------------------|-------------|
| `layout accordion` | ✅ `layout stacked` (sehr ähnlich) |
| `move-mouse window-lazy-center` | ✅ `mouse_warping container` |
| `workspace-back-and-forth` | ✅ Identisch |
| Per-Monitor Gaps | ⚠️ Nicht nativ, aber per Output konfigurierbar |
| `flatten-workspace-tree` | ⚠️ Manuell mit `layout splith` |

## Tipps für Ubuntu

1. **GDM (GNOME Display Manager)** zeigt Sway automatisch als Option
2. **XWayland** ist standardmäßig aktiviert für X11-Apps
3. Für **Screen Sharing** in Browsern: Firefox funktioniert besser als Chrome
4. **Electron-Apps** (VS Code, Slack): Mit `--enable-features=UseOzonePlatform --ozone-platform=wayland` starten

## Weitere Konfiguration

- **Waybar Config**: `~/.config/waybar/config`
- **Mako Config**: `~/.config/mako/config`
- **Wofi Config**: `~/.config/wofi/config`
