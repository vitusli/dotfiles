# i3 Konfiguration (AeroSpace-Äquivalent)

Diese i3-Konfiguration ist eine Übersetzung der AeroSpace-Konfiguration von macOS.

## Abhängigkeiten

Um die gleiche Erfahrung wie mit AeroSpace auf macOS zu haben, benötigst du folgende Pakete:

### Pflicht

| Paket | Beschreibung | Installation |
|-------|--------------|--------------|
| **i3-gaps** | i3 mit Gap-Support | `sudo pacman -S i3-gaps` (Arch) / `sudo apt install i3-gaps` (Debian/Ubuntu) |
| **xdotool** | Maus-Steuerung (für move-mouse Funktionalität) | `sudo pacman -S xdotool` / `sudo apt install xdotool` |
| **xrandr** | Monitor-Konfiguration | Meist vorinstalliert, sonst: `sudo apt install x11-xserver-utils` |

### Empfohlen

| Paket | Beschreibung | Installation |
|-------|--------------|--------------|
| **picom** | Compositor (Transparenz, Animationen, Schatten) | `sudo pacman -S picom` / `sudo apt install picom` |
| **polybar** | Statusleiste (besser als i3bar) | `sudo pacman -S polybar` / aus AUR oder PPA |
| **rofi** | App-Launcher (wie Spotlight) | `sudo pacman -S rofi` / `sudo apt install rofi` |
| **feh** | Hintergrundbild setzen | `sudo pacman -S feh` / `sudo apt install feh` |
| **dunst** | Benachrichtigungen | `sudo pacman -S dunst` / `sudo apt install dunst` |

## Setup

### 1. Pakete installieren

```bash
# Arch Linux
sudo pacman -S i3-gaps xdotool picom polybar rofi feh dunst

# Debian/Ubuntu
sudo apt install i3-gaps xdotool picom rofi feh dunst
# polybar ggf. aus PPA oder manuell bauen
```

### 2. Monitor-Namen herausfinden

```bash
xrandr --query | grep " connected"
```

Passe dann in der `config` die Zeilen an:
```
workspace 1 output <DEIN_HAUPTMONITOR>
workspace 2 output <DEIN_ZWEITMONITOR>
```

### 3. Autostart-Skript erstellen (optional)

Erstelle `~/.config/i3/autostart.sh`:

```bash
#!/bin/bash

# Compositor starten
picom --daemon

# Hintergrundbild setzen
feh --bg-scale ~/Bilder/wallpaper.jpg

# Benachrichtigungen
dunst &

# Maus zum aktiven Fenster bewegen (ähnlich on-focus-changed)
# Kann mit xdotool in einem Skript realisiert werden
```

Dann in der i3-config hinzufügen:
```
exec_always --no-startup-id ~/.config/i3/autostart.sh
```

## Unterschiede zu AeroSpace

| AeroSpace Feature | i3 Äquivalent | Status |
|-------------------|---------------|--------|
| `layout accordion` | `layout stacked` | ⚠️ Ähnlich, nicht identisch |
| `layout v_accordion` | `layout stacked` + `split v` | ⚠️ Ähnlich |
| `move-mouse window-lazy-center` | `xdotool` Skript | ⚠️ Manuell |
| `flatten-workspace-tree` | `layout splith` | ⚠️ Nur teilweise |
| Monitor-spezifische Gaps | Nicht nativ | ❌ Workaround nötig |
| `close-all-windows-but-current` | Skript nötig | ⚠️ Manuell |

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
| `q` | i3 neustarten |
| `e` | Layout zurücksetzen |
| `f` | Floating toggle |
| `Backspace` | Andere Fenster schließen |
| `Escape` | Service-Modus verlassen |

## Tipps

- **stacked** ist das nächste Äquivalent zu AeroSpace's accordion
- Nutze `tabbed` wenn du Tabs statt gestapelter Fenster willst
- Für echte 1:1 Parität könntest du auch **Sway** (Wayland) in Betracht ziehen
