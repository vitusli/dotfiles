# Dotfiles

Cross-platform dotfiles for macOS and Windows.

## Structure

```
dotfiles/
├── macOS/           # macOS dotfiles (chezmoi)
│   ├── chezmoi/     # config files
│   ├── macme.sh     # setup script
│   └── README.md
├── windows/         # Windows dotfiles (chezmoi)
│   ├── chezmoi/     # config files
│   ├── windowme.ps1 # setup script
│   └── README.md
└── logs/            # setup logs
```

## Quick Start (read the scripts - this will change your system)

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macOS/macme.sh | zsh
```

### Windows

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/windows/windowme.ps1 | iex
```

## Details

- [macOS README](macOS/README.md) - chezmoi, Homebrew, zsh
- [Windows README](windows/README.md) - chezmoi, Scoop, PowerShell

### ChezMoi SourceDir (macOS)

If `chezmoi apply` does not pick up this repository automatically, set the source directory once and apply:

```bash
chezmoi init --source "$HOME/dotfiles/macOS/chezmoi"
chezmoi apply
```

Alternatively, configure a default source for future runs:

```bash
mkdir -p "$HOME/.config/chezmoi"
printf 'sourceDir: %s\n' "$HOME/dotfiles/macOS/chezmoi" > "$HOME/.config/chezmoi/chezmoi.yaml"
```

### ChezMoi SourceDir (Windows)

If `chezmoi apply` does not see this repo yet, initialize with the local source and apply:

```powershell
chezmoi init --source "$env:USERPROFILE\\dotfiles\\windows\\chezmoi"
chezmoi apply
```

Optionally set a persistent default source:

```powershell
$cfg = "$env:APPDATA\\chezmoi\\chezmoi.yaml"
New-Item -ItemType Directory -Force (Split-Path $cfg) | Out-Null
"sourceDir: $env:USERPROFILE\\dotfiles\\windows\\chezmoi" | Set-Content $cfg
```
