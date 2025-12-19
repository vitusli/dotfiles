# Windows Dotfiles

Verwaltung von Windows-Konfigurationsdateien mit chezmoi.

## Setup

Einmalig auf neuem System:

```powershell
# Pfad als Argument setzt die Source, --apply kopiert alles inkl. chezmoi.toml
chezmoi init C:\Users\Vitus\dotfiles\windows\chezmoi --apply
```

Danach reicht `chezmoi apply` (Pfad ist in ~/.config/chezmoi/chezmoi.toml gespeichert).

Aktuellen Source-Pfad prüfen:

```powershell
chezmoi source-path
```

## Täglicher Workflow

Nach Änderungen in `chezmoi/` anwenden:

```powershell
chezmoi apply
```

Datei bearbeiten (öffnet Source in VS Code, applied automatisch nach Speichern):

```powershell
chezmoi edit $PROFILE
chezmoi edit ~/.config/wezterm/wezterm.lua
```

Oder mit fzf:

```powershell
stow   # fuzzy-select und edit
```

## Verwaltete Dateien

- PowerShell Profile (`Dokumente/PowerShell/Microsoft.PowerShell_profile.ps1`)
- Wezterm Konfiguration (`.config/wezterm/wezterm.lua`)
- VS Code Settings & Keybindings (`AppData/Roaming/Code/User/`)
- Bash/Inputrc (`.bashrc`, `.bash_profile`, `.inputrc`)
- Chezmoi Config (`.config/chezmoi/chezmoi.toml`)

## Struktur

```
dotfiles/
├── windows/
│   ├── chezmoi/                          # chezmoi dotfiles
│   │   ├── Dokumente/PowerShell/
│   │   ├── dot_config/wezterm/
│   │   ├── dot_config/chezmoi/
│   │   └── AppData/Roaming/Code/User/
│   ├── ahkv1/                            # AutoHotkey v1 scripts
│   ├── windowme.ps1                      # Windows setup script
│   └── README.md
└── macOS/                                # macOS dotfiles (stow)
```


