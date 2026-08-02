# Dotfiles

Cross-platform dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Package installation and Dotfiles Setup

Without a chezmoi installation (Unix):
```bash
BINDIR="$HOME/.local/bin" sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply --verbose vitusli
```

With chezmoi already installed:
```bash
chezmoi init --apply --verbose vitusli
```

## macOS Bootstrap

Install Apple's Command Line Tools first (required by Homebrew on a fresh Mac):
```bash
xcode-select --install
```

Then run the bootstrap template.

Robust variant (works even if `chezmoi` is not yet in your current shell `PATH`):
```bash
"$HOME/.local/bin/chezmoi" execute-template < "$("$HOME/.local/bin/chezmoi" source-path)/bootstrap/bootstrap_macos.sh.tmpl" | bash
```

If `chezmoi` is already available in `PATH`:
```bash
chezmoi execute-template < "$(chezmoi source-path)/bootstrap/bootstrap_macos.sh.tmpl" | bash
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
