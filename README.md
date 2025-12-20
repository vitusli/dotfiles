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
chezmoi init vitusli/dotfiles --source ~/dotfiles/macOS/chezmoi --apply
```
### Windows

```powershell
chezmoi init vitusli/dotfiles --source $env:USERPROFILE\dotfiles\windows\chezmoi --apply
```


## Updating on Existing Machines

After initial setup, update your dotfiles from the remote repository:

```bash
chezmoi update -v
```

This pulls the latest changes from GitHub and applies them to your system (combines `git pull` + `chezmoi apply`).

## Details

- [macOS README](macOS/README.md) - chezmoi, Homebrew, zsh
- [Windows README](windows/README.md) - chezmoi, Scoop, PowerShell
