# Dotfiles

Cross-platform dotfiles for macOS, Windows, and Linux/WSL.

## Structure

```
dotfiles/
├── main branch      # This README + bootstrap scripts
├── macos branch     # macOS dotfiles (chezmoi source)
├── windows branch   # Windows dotfiles (chezmoi source)
└── linux branch     # Linux/WSL dotfiles (chezmoi source)
```

## Quick Start

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macme.sh | zsh
```

Or manually:
```bash
chezmoi init --branch macos vitusli --apply
```

### Windows

```powershell
chezmoi init --branch windows vitusli --apply
```

### Linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linuxme.sh | bash
```

Or manually:
```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply vitusli --branch linux
```

## Updating on Existing Machines

After initial setup, update your dotfiles from the remote repository:

```bash
chezmoi update -v
```

This pulls the latest changes from GitHub and applies them to your system (combines `git pull` + `chezmoi apply`).
