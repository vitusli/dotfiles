# Linux/WSL Dotfiles

Zsh configuration for Linux and Windows Subsystem for Linux (WSL).

## Quick Install

```bash
# 1. Install chezmoi and initialize
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply vitusli/dotfiles --branch linux

# 2. Set zsh as default shell
chsh -s $(which zsh)
```

## Prerequisites

Install required packages on Ubuntu/Debian:

```bash
sudo apt update && sudo apt install -y \
  zsh \
  fzf \
  bat \
  zsh-autosuggestions \
  zsh-syntax-highlighting

# Optional but recommended:
sudo apt install -y \
  zoxide \
  lf
```

## Features

- **Vim mode** with cursor shape change (block/line)
- **WSL clipboard integration** (yank copies to Windows clipboard via `clip.exe`)
- **fzf fuzzy finder** with `/` command for quick file navigation
- **zsh-autosuggestions** and **zsh-syntax-highlighting**
- **zoxide** for smart directory jumping
- **chezmoi** integration with `stow` command

## File Structure

```
~/.zshrc          # Main config, loads modules
~/.zprofile       # Login shell PATH setup
~/.zsh/
  ├── completion.zsh   # Completions & plugins
  ├── functions.zsh    # Custom functions (/, stow, lf)
  └── vim-mode.zsh     # Vim keybindings & clipboard
```

## Key Commands

| Command | Description |
|---------|-------------|
| `/` | Fuzzy find files/dirs, open in app |
| `/ code` | Fuzzy find, open directly in VS Code |
| `stow` | Edit chezmoi-managed files with fzf |
| `z <dir>` | Jump to frequently used directory |

## WSL Notes

- Clipboard: Uses `clip.exe` for Windows clipboard integration
- VS Code: Install "Remote - WSL" extension for seamless `code` command
