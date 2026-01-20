# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Structure

| Branch | Platform |
|--------|----------|
| `main` | Shared dotfiles for MacOS and Windows |
| `linux` | Arch dotfiles, one day also in main branch |

## Bootstrap

### MacOS

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/macos.sh | zsh
```

Run specific parts of the setup by passing flags:

```bash
zsh macos.sh --help
```
```bash
zsh <(curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/macos.sh) --defaults --softwareupdate
```

### Windows (WIP)

```powershell
irm https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/windows.ps1 | iex
```

### Arch Linux (untested)

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/bootstrap/linux.sh | bash
```

## Dotfiles Setup

```bash
chezmoi init --branch <branch> vitusli --apply
```

## Update

```bash
chezmoi update -v
```
