#!/bin/zsh
# Update vendored vim plugins (fzf & fzf.vim)
# Usage: cd ~/dotfiles && ./stow/.vim/update-plugins.sh

set -e

PLUGINS_DIR="${0:h}/pack/plugins/start"
cd "$PLUGINS_DIR"

echo "Updating vim plugins in $PLUGINS_DIR..."

# Remove old versions
echo "Removing old plugin versions..."
rm -rf fzf fzf.vim wilder.nvim

# Clone fresh, then remove .git to vendor them
echo "Cloning fresh plugins..."
git clone --depth 1 https://github.com/junegunn/fzf.git
git clone --depth 1 https://github.com/junegunn/fzf.vim.git
git clone --depth 1 https://github.com/gelguy/wilder.nvim.git

echo "Removing .git directories (vendoring)..."
rm -rf fzf/.git fzf.vim/.git wilder.nvim/.git

# Stage and commit
echo "Committing changes..."
cd "${0:h:h:h}" # Back to dotfiles root
git add -f stow/.vim/pack/plugins/start/fzf stow/.vim/pack/plugins/start/fzf.vim stow/.vim/pack/plugins/start/wilder.nvim
git commit -m "update: vim plugins fzf + fzf.vim + wilder.nvim"

echo "✓ Vim plugins updated successfully"
echo "Run 'git push' to push changes"
