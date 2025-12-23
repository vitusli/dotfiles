# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Structure

| Branch | Platform |
|--------|----------|
| `main` | Bootstrap scripts |
| `macos` | macOS dotfiles |
| `windows` | Windows dotfiles |
| `linux` | Linux/WSL dotfiles |

## Bootstrap

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macos.sh | zsh
```

### Windows

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/windows.ps1 | iex
```

### Linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linux.sh | bash
```

## Manual Setup

Requires SSH key or `gh auth login`:

```bash
chezmoi init --branch <platform> vitusli --apply
```

## Update

```bash
chezmoi update -v
```

