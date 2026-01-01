# Arch Linux Installation Guide

> Für Design/Dev Workflow mit Sway, Blender, VS Code und RTX 3090

## Übersicht

1. USB-Stick erstellen
2. Arch mit `archinstall` installieren
3. Reboot & Login
4. `arch.sh` Bootstrap Script ausführen

---

## Phase 1: USB-Stick erstellen

### Auf macOS:
```bash
# 1. Arch ISO downloaden
# https://archlinux.org/download/

# 2. USB-Stick finden
diskutil list
# → z.B. /dev/disk4

# 3. Unmounten
diskutil unmountDisk /dev/disk4

# 4. ISO auf USB schreiben (ACHTUNG: disk4 durch deine Disk ersetzen!)
sudo dd if=~/Downloads/archlinux-*.iso of=/dev/rdisk4 bs=4M status=progress

# 5. Auswerfen
diskutil eject /dev/disk4
```

### Auf Windows:
1. [Rufus](https://rufus.ie) herunterladen und starten
2. USB-Stick einstecken
3. Bei "Boot selection" → SELECT → die heruntergeladene `archlinux-*.iso` Datei wählen
4. Alles andere auf Standard lassen
5. START klicken → Warten bis fertig

---

## Phase 2: Arch Installation

### 2.1 Booten
1. PC neustarten
2. Boot-Menü öffnen (meist F12, F2, oder DEL)
3. USB-Stick auswählen
4. "Arch Linux install medium" wählen

### 2.2 Netzwerk (WiFi)
```bash
# Falls WiFi nötig:
iwctl
> station wlan0 scan
> station wlan0 get-networks
> station wlan0 connect "DEIN-WIFI-NAME"
> exit

# Testen:
ping -c 3 archlinux.org
```

### 2.3 archinstall starten
```bash
archinstall
```

### 2.4 archinstall Einstellungen

| Option | Empfehlung | Erklärung |
|--------|------------|-----------|
| **Language** | English | Menüsprache, English = bessere Fehlermeldungen |
| **Mirrors** | Germany | Download-Server in deiner Nähe |
| **Locales** | `de_DE.UTF-8` | Systemsprache (Datum/Zahlenformat) |
| **Disk configuration** | Use best-effort | Automatische Partitionierung |
| **Disk** | Deine Haupt-SSD | z.B. `nvme0n1` oder `sda` |
| **Filesystem** | ext4 | Einfach und stabil |
| **Disk encryption** | No | Optional, macht Debugging schwerer |
| **Bootloader** | systemd-boot | Einfacher als GRUB |
| **Swap** | True | Für Suspend/Hibernate |
| **Hostname** | z.B. `archbox` | **PC-Name** im Netzwerk (nicht dein Username!) |
| **Root password** | Setzen! | Admin-Passwort |
| **User account** | Erstellen! | **Dein Username** + Passwort + sudo aktivieren |
| **Profile** | **Minimal** | ← WICHTIG! Kein Desktop wählen |
| **Audio** | Pipewire | Modernes Audio-System |
| **Kernels** | linux | NICHT linux-lts (wegen NVIDIA) |
| **Additional packages** | `git base-devel curl wget networkmanager` | Basics |
| **Network configuration** | NetworkManager | Für WiFi |
| **Timezone** | Europe/Berlin | Deine Zeitzone |

### 2.5 Installation starten
1. "Install" wählen
2. Warten (5-15 Minuten) - Kaffee holen ☕
3. Am Ende fragt er: **"Would you like to chroot into the installation?"**
   - Wähle **No**
4. Du bist wieder im Terminal. Tippe:
   ```bash
   reboot
   ```
5. **Sofort USB-Stick rausziehen** während er neustartet

---

## Phase 3: Erster Boot

### 3.1 Login
Nach dem Reboot siehst du einen schwarzen Bildschirm mit Text:
```
archbox login: _
```

1. Tippe deinen **Username** (den du bei "User account" erstellt hast), Enter
2. Tippe dein **Passwort** (wird nicht angezeigt!), Enter
3. Du siehst jetzt eine Shell:
   ```
   [vitus@archbox ~]$ _
   ```

### 3.2 Netzwerk starten
```bash
# NetworkManager aktivieren (falls nicht schon)
sudo systemctl enable --now NetworkManager

# WiFi verbinden (falls nötig)
nmcli device wifi connect "DEIN-WIFI" password "DEIN-PASSWORT"

# Testen
ping -c 3 google.com
```

### 3.3 Bootstrap Script ausführen
```bash
# Script herunterladen und ausführen
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/arch.sh | bash
```

Das Script installiert:
- NVIDIA Treiber (für RTX 3090)
- Sway + Waybar + Wofi
- Audio (Pipewire)
- yay (AUR Helper)
- Homebrew + CLI Tools (fzf, bat, lazygit, etc.)
- VS Code, Blender, Firefox
- Ulauncher, Espanso
- Deine Dotfiles via chezmoi

---

## Phase 4: Sway starten

Nach dem Script:
```bash
# Ausloggen und neu einloggen, oder:
exec zsh

# Sway starten (in TTY, nicht in GUI)
sway
```

### Auto-Login in Sway
Das Script fügt automatisch zu `~/.zprofile` hinzu:
```bash
# Start Sway on TTY1
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec sway
fi
```

Das bedeutet: Wenn du dich auf TTY1 einloggst → Sway startet automatisch.

> **Warum .zprofile und nicht .zshrc?**  
> `.zprofile` wird nur beim Login ausgeführt.  
> `.zshrc` wird bei jeder neuen Shell ausgeführt (auch in Terminals innerhalb Sway).

---

## Troubleshooting

### Schwarzer Bildschirm nach Sway-Start?
```bash
# Ctrl+Alt+F2 für TTY2
# Logs checken:
cat ~/.local/share/sway/sway.log
journalctl -b -p err
```

### NVIDIA nicht erkannt?
```bash
# Treiber geladen?
lsmod | grep nvidia

# GPU Info
nvidia-smi
```

### Kein Sound?
```bash
# Pipewire Status
systemctl --user status pipewire wireplumber

# Neustart
systemctl --user restart pipewire wireplumber
```

### WiFi geht nicht?
```bash
# NetworkManager Status
systemctl status NetworkManager

# Netzwerke anzeigen
nmcli device wifi list
```

---

## Nützliche Befehle

```bash
# System updaten
sudo pacman -Syu

# Paket suchen
pacman -Ss suchbegriff

# AUR Paket installieren
yay -S paketname

# Logs anschauen
journalctl -b          # Boot-Log
journalctl -f          # Live-Log

# Service Status
systemctl status servicename
```

---

## Nach der Installation

1. **Browser öffnen** → GitHub, etc. einloggen
2. **VS Code** → Extensions installieren
3. **Blender** → CUDA/OptiX prüfen (Edit → Preferences → System)
4. **Dotfiles anpassen** → `chezmoi edit ~/.config/sway/config`
