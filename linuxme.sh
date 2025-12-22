#!/bin/bash

# Download and run with bash:
# curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linuxme.sh | bash

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================
LOG_FILE="$HOME/.local/share/chezmoi-setup-$(date +%Y%m%d-%H%M%S).log"

# APT packages for zsh environment
APT_PACKAGES=(
    zsh
    fzf
    bat
    xclip
    zsh-autosuggestions
    zsh-syntax-highlighting
    curl
    git
    zoxide
    lf
)

# Optional packages (nice to have)
APT_OPTIONAL=(
    zoxide
    lf
    vim
    neovim
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_header() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "▶ $1"
    echo "════════════════════════════════════════════════════════════"
    echo "" >> "$LOG_FILE"
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "▶ $1" >> "$LOG_FILE"
}

log_success() {
    echo "✓ $1"
    echo "✓ $1" >> "$LOG_FILE"
}

log_info() {
    echo "ℹ $1"
    echo "ℹ $1" >> "$LOG_FILE"
}

log_warning() {
    echo "⚠ $1"
    echo "⚠ $1" >> "$LOG_FILE"
}

log_error() {
    echo "✗ $1"
    echo "✗ $1" >> "$LOG_FILE"
}

command_exists() {
    command -v "$1" &> /dev/null
}

# ============================================================================
# APT PACKAGES
# ============================================================================

install_apt_packages() {
    log_header "Installing APT Packages"
    
    log_info "Updating package lists..."
    sudo apt update >> "$LOG_FILE" 2>&1
    
    local to_install=()
    
    for pkg in "${APT_PACKAGES[@]}"; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            log_success "$pkg (already installed)"
        else
            to_install+=("$pkg")
            log_warning "$pkg (will be installed)"
        fi
    done
    
    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "Installing ${#to_install[@]} packages..."
        sudo apt install -y "${to_install[@]}" >> "$LOG_FILE" 2>&1
        log_success "APT packages installed"
    else
        log_info "All required packages already installed"
    fi
}

install_optional_packages() {
    log_header "Installing Optional Packages"
    
    for pkg in "${APT_OPTIONAL[@]}"; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            log_success "$pkg (already installed)"
        else
            log_info "Installing $pkg..."
            sudo apt install -y "$pkg" >> "$LOG_FILE" 2>&1 && \
                log_success "$pkg installed" || \
                log_warning "$pkg not available in repos"
        fi
    done
}

# ============================================================================
# CHEZMOI SETUP
# ============================================================================

install_chezmoi() {
    log_header "Installing chezmoi"
    
    if command_exists chezmoi; then
        log_success "chezmoi already installed"
    else
        log_info "Installing chezmoi..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b ~/.local/bin >> "$LOG_FILE" 2>&1
        export PATH="$HOME/.local/bin:$PATH"
        log_success "chezmoi installed to ~/.local/bin"
    fi
}

apply_dotfiles() {
    log_header "Applying Dotfiles with chezmoi"
    
    if [ -f "$HOME/.zshrc" ] && chezmoi verify &>/dev/null 2>&1; then
        log_success "Dotfiles already applied"
    else
        log_info "Initializing and applying dotfiles..."
        chezmoi init --branch linux vitusli --apply 2>&1 | tee -a "$LOG_FILE"
        log_success "Dotfiles applied"
    fi
}

# ============================================================================
# SHELL SETUP
# ============================================================================

setup_zsh_default() {
    log_header "Setting zsh as Default Shell"
    
    if [ "$SHELL" = "$(which zsh)" ]; then
        log_success "zsh is already the default shell"
    else
        log_info "Changing default shell to zsh..."
        chsh -s "$(which zsh)"
        log_success "Default shell changed to zsh"
        log_info "Please log out and back in for the change to take effect"
    fi
}

# ============================================================================
# WSL SPECIFIC
# ============================================================================

setup_wsl_extras() {
    log_header "WSL Configuration"
    
    # Check if running in WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_info "Detected WSL environment"
        
        # Ensure ~/.local/bin exists
        mkdir -p "$HOME/.local/bin"
        
        # VS Code should work out of the box in WSL
        if command_exists code; then
            log_success "VS Code available via 'code' command"
        else
            log_warning "VS Code not detected - install 'Remote - WSL' extension in Windows VS Code"
        fi
        
        # Clipboard works via clip.exe
        if command_exists clip.exe; then
            log_success "Windows clipboard available via clip.exe"
        fi
    else
        log_info "Native Linux environment (not WSL)"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo "════════════════════════════════════════════════════════════"
    echo "  Linux/WSL Setup Script"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "This script will install:"
    echo "  - zsh with plugins (autosuggestions, syntax-highlighting)"
    echo "  - fzf, bat, and other CLI tools"
    echo "  - chezmoi for dotfile management"
    echo "  - Apply dotfiles from github.com/vitusli/dotfiles"
    echo ""
    echo "Log file: $LOG_FILE"
    echo ""
    
    # Initialize log
    mkdir -p "$(dirname "$LOG_FILE")"
    {
        echo "════════════════════════════════════════════════════════════"
        echo "Linux/WSL Setup Log"
        echo "Start: $(date)"
        echo "User: $(whoami)"
        echo "Host: $(hostname)"
        echo "════════════════════════════════════════════════════════════"
    } > "$LOG_FILE"
    
    # Run setup
    install_apt_packages
    install_optional_packages
    install_chezmoi
    apply_dotfiles
    setup_wsl_extras
    setup_zsh_default
    
    # Done
    log_header "Setup Complete!"
    echo ""
    echo "✓ All done! Start a new terminal or run: exec zsh"
    echo ""
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "End: $(date)" >> "$LOG_FILE"
}

main "$@"
