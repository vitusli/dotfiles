# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

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