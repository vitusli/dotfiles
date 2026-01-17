#!/bin/bash
# Vim Plugin Manager using git submodules
# Usage: ./dot_vim/plugin_manager.sh [install|update|remove <plugin>]

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOTFILES_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGINS_DIR="$SCRIPT_DIR/pack/plugins/start"

cd "$DOTFILES_ROOT"

# Apply changes to the target system via chezmoi
apply_chezmoi() {
  if command -v chezmoi >/dev/null 2>&1; then
    echo "Applying dotfiles with chezmoi..."
    if chezmoi apply; then
      echo "✓ chezmoi apply completed"
    else
      echo "✗ chezmoi apply failed"
      exit 1
    fi
  else
    echo "chezmoi not installed; skipping auto-apply"
  fi
}

case "${1:-install}" in
  install)
    echo "Installing vim plugins as submodules..."
    mkdir -p "$PLUGINS_DIR"

    # Add plugins as submodules
    git submodule add --force https://github.com/junegunn/fzf.git "$PLUGINS_DIR/fzf" 2>/dev/null || echo "✓ fzf already exists"
    git submodule add --force https://github.com/junegunn/fzf.vim.git "$PLUGINS_DIR/fzf.vim" 2>/dev/null || echo "✓ fzf.vim already exists"
    git submodule add --force https://github.com/gelguy/wilder.nvim.git "$PLUGINS_DIR/wilder.nvim" 2>/dev/null || echo "✓ wilder.nvim already exists"
    git submodule add --force https://github.com/tpope/vim-surround.git "$PLUGINS_DIR/vim-surround" 2>/dev/null || echo "✓ vim-surround already exists"

    git submodule update --init --recursive
    echo "✓ All plugins installed"
    apply_chezmoi
    ;;

  update)
    echo "Updating vim plugins..."
    git submodule update --remote --merge
    echo "✓ All plugins updated"
    apply_chezmoi
    ;;

  remove)
    if [ -z "$2" ]; then
      echo "Usage: $0 remove <plugin-name>"
      exit 1
    fi
    echo "Removing plugin: $2..."
    git submodule deinit -f "$PLUGINS_DIR/$2"
    git rm -f "$PLUGINS_DIR/$2"
    rm -rf ".git/modules/dot_vim/pack/plugins/start/$2"
    echo "✓ Plugin $2 removed"
    apply_chezmoi
    ;;

  *)
    echo "Usage: $0 [install|update|remove <plugin>]"
    exit 1
    ;;
esac
