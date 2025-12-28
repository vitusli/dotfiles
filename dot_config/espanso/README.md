# espanso - Text Expander (Raycast Snippets Alternative)

espanso ist ein cross-platform Text Expander – ähnlich wie Raycast Snippets.

## Installation auf Ubuntu

```bash
# Snap (einfachste Methode)
sudo snap install espanso --classic

# Oder: Debian-Paket von GitHub
# https://github.com/espanso/espanso/releases
```

## Wayland-Konfiguration

Für Wayland (Sway) muss espanso im `clipboard` Backend laufen. Das ist in `config/default.yml` bereits konfiguriert.

## Snippets hinzufügen

Bearbeite `match/base.yml` oder erstelle neue `.yml` Dateien in `match/`:

```yaml
matches:
  - trigger: ":gruss"
    replace: "Hallo, wie geht's?"
```

## Enthaltene Snippets

| Trigger | Ersetzung |
|---------|-----------|
| `:date` | Aktuelles Datum (2025-12-28) |
| `:time` | Aktuelle Uhrzeit (22:55) |
| `:now` | Datum + Uhrzeit |
| `:mail` | Deine E-Mail |
| `:sig` | E-Mail-Signatur |
| `:shebang` | `#!/usr/bin/env bash` |
| `:py` | Python Shebang |
| `:arrow` | → |
| `:check` | ✓ |
| `:x` | ✗ |
| `:shrug` | ¯\_(ツ)_/¯ |
| `:lorem` | Lorem Ipsum Text |

## Autostart mit Sway

Füge in `~/.config/sway/config` hinzu:

```
exec espanso daemon
```

## Mehr Infos

- Dokumentation: https://espanso.org/docs/
- Hub (fertige Pakete): https://hub.espanso.org/
