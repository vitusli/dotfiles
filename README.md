# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Structure

| Branch | Platform |
|--------|----------|
| `main` | Bootstrap scripts |
| `macos` | MacOS dotfiles |
| `windows` | Windows dotfiles |
| `linux` | Arch dotfiles |

## Bootstrap

### MacOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macos.sh | zsh
```

### Windows

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/windows.ps1 | iex
```

### Arch Linux

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

## Config

Shared package lists in `config/`. Use `#macos`, `#linux`, or `#windows` tags for platform-specific packages. Untagged = all platforms.

