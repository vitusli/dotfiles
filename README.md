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

## macOs Bootstrap

Manual invocation via chezmoi execute-template:

Install Apple's Command Line Tools first. Homebrew needs them on a fresh Mac:
```bash
xcode-select --install
```

```bash
chezmoi execute-template < ~/.local/share/chezmoi/run_once_bootstrap_macos.sh.tmpl | bash
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
