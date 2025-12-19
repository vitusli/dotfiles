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
