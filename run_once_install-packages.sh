#!/bin/bash

# =============================================================================
# Homebrew Package Installation (idempotent)
# This script is run once by chezmoi to install required packages.
# =============================================================================

set -e

# Check if Homebrew is installed
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

echo "Installing Homebrew packages..."

# =============================================================================
# Formulae (CLI tools)
# =============================================================================
FORMULAE=(
    zsh-autosuggestions
    zsh-syntax-highlighting
    zsh-abbr
    zoxide
    fzf
    lf
    neovim
    lazygit
    bat
    # Preview dependencies (for lf)
    poppler      # pdftotext
    p7zip        # 7z
    unar         # rar support
)

# =============================================================================
# Casks (GUI applications)
# =============================================================================
CASKS=(
    aerospace
    wezterm
    karabiner-elements
    alt-tab
)

# =============================================================================
# Install packages (idempotent - brew handles already installed packages)
# =============================================================================

echo "Installing formulae..."
for formula in "${FORMULAE[@]}"; do
    if ! brew list --formula "$formula" &>/dev/null; then
        echo "  Installing $formula..."
        brew install "$formula"
    else
        echo "  $formula already installed"
    fi
done

echo "Installing casks..."
for cask in "${CASKS[@]}"; do
    if ! brew list --cask "$cask" &>/dev/null; then
        echo "  Installing $cask..."
        brew install --cask "$cask"
    else
        echo "  $cask already installed"
    fi
done

echo "Homebrew package installation complete!"
