# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Bootstrap

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/macos.sh | zsh
```

### Windows

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/windows.ps1 | iex
```

### Linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/linux.sh | bash
```

## Manual setup for dotfiles

Requires SSH key or `gh auth login`:

```bash
chezmoi init vitusli --apply
```

## Update

```bash
chezmoi update -v
```

