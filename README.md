# Dotfiles

Cross-platform dotfiles for macOS and Windows.

## Structure

```
dotfiles/
├── main branch      # This README
├── macos branch     # macOS dotfiles (chezmoi source)
└── windows branch   # Windows dotfiles (chezmoi source)
```

## Quick Start

### macOS

```bash
chezmoi init --branch macos vitusli --apply
```

### Windows

```powershell
chezmoi init --branch windows vitusli --apply
```

## Updating on Existing Machines

After initial setup, update your dotfiles from the remote repository:

```bash
chezmoi update -v
```

This pulls the latest changes from GitHub and applies them to your system (combines `git pull` + `chezmoi apply`).
