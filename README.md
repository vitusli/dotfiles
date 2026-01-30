# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Structure

| Branch | Platform |
|--------|----------|
| `main` | Shared dotfiles for MacOS and Windows |
| `linux` | Arch dotfiles, one day also in main branch |

## Dotfiles Setup

Without a chezmoi installation, unix only
```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply --verbose vitusli
 
```
With chezmoi installed
```
chezmoi init --apply --verbose vitusli 
```

## Update

local
```bash
chezmoi apply -v
```
remote
```bash
chezmoi update -v
```