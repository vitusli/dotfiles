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

### windows

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/wina.ps1 | iex
```

### linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linu.sh | bash
```


Or apply your dotfiles manually (requires SSH key or `gh auth login` first):

### macOS
```bash
chezmoi init --branch macos vitusli --apply
```

### Windows

```powershell
chezmoi init --branch windows vitusli --apply
```

### Linux / WSL

```zsh
chezmoi init --branch linux vitusli --apply
```


## Updating on Existing Machines

After initial setup, update your dotfiles from the remote repository:

```bash
chezmoi update -v
```

This pulls the latest changes from GitHub and applies them to your system (combines `git pull` + `chezmoi apply`).

