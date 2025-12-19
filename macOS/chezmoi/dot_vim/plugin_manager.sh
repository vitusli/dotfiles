#!/bin/zsh
# Vim Plugin Manager using git submodules
# Usage: ./macOS/chezmoi/dot_vim/plugin_manager.sh [install|update|remove <plugin>]

set -e

DOTFILES_ROOT="${0:h:h:h}"
PLUGINS_DIR="${0:h}/pack/plugins/start"

cd "$DOTFILES_ROOT"

case "${1:-install}" in
  install)
    echo "Installing vim plugins as submodules..."
    mkdir -p "$PLUGINS_DIR"
    
    # Add plugins as submodules
    git submodule add --force https://github.com/junegunn/fzf.git "$PLUGINS_DIR/fzf" 2>/dev/null || echo "✓ fzf already exists"
    git submodule add --force https://github.com/junegunn/fzf.vim.git "$PLUGINS_DIR/fzf.vim" 2>/dev/null || echo "✓ fzf.vim already exists"
    git submodule add --force https://github.com/gelguy/wilder.nvim.git "$PLUGINS_DIR/wilder.nvim" 2>/dev/null || echo "✓ wilder.nvim already exists"
    
    git submodule update --init --recursive
    echo "✓ All plugins installed"
    ;;
    
  update)
    echo "Updating vim plugins..."
    git submodule update --remote --merge
    echo "✓ All plugins updated"
    ;;
    
  remove)
    if [[ -z "$2" ]]; then
      echo "Usage: $0 remove <plugin-name>"
      exit 1
    fi
    echo "Removing plugin: $2..."
    git submodule deinit -f "$PLUGINS_DIR/$2"
    git rm -f "$PLUGINS_DIR/$2"
    rm -rf ".git/modules/macOS/chezmoi/dot_vim/pack/plugins/start/$2"
    echo "✓ Plugin $2 removed"
    ;;
    
  *)
    echo "Usage: $0 [install|update|remove <plugin>]"
    exit 1
    ;;
esac
