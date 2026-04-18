# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Dotfiles Setup

Without a chezmoi installation, unix only
```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply --verbose --branch wsl_exploration vitusli
 
```
With chezmoi installed
```
chezmoi init --apply --verbose --branch wsl_exploration vitusli
```

## Bootstrap

Run from your chezmoi source directory (`~/.local/share/chezmoi`):

One-time bootstrap:
- `run_once_bootstrap_macos.sh.tmpl`
- `run_once_bootstrap_wsl.sh.tmpl`
- `run_once_bootstrap_windows.ps1.tmpl`

Manual invocation via chezmoi execute-template:

macOS
```bash
chezmoi execute-template < ~/.local/share/chezmoi/run_once_bootstrap_macos.sh.tmpl | bash
```

WSL (Ubuntu)
```bash
chezmoi execute-template < ~/.local/share/chezmoi/run_once_bootstrap_wsl.sh.tmpl | bash
```

Windows (PowerShell)
```powershell
chezmoi execute-template < $env:USERPROFILE\.local\share\chezmoi\run_once_bootstrap_windows.ps1.tmpl | Invoke-Expression
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