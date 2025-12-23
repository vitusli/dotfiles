#!/bin/bash

# Download and run with bash:
# curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linu.sh | bash

# Don't use set -e because some commands may fail non-fatally
set +e

# ============================================================================
# CONFIGURATION
# ============================================================================
LOG_FILE="$HOME/.local/share/chezmoi-setup-$(date +%Y%m%d-%H%M%S).log"

# Homebrew packages (same as macOS where possible!)
BREW_PACKAGES=(
    fzf
    bat
    lazygit
    lf
    gh
    zoxide
    chezmoi
    zsh-autosuggestions
    zsh-syntax-highlighting
)

# Packages from taps (need to be installed separately)
BREW_TAP_PACKAGES=(
    "olets/tap/zsh-abbr"
)

# Minimal APT packages (only what Homebrew can't provide)
APT_PACKAGES=(
    build-essential
    curl
    git
    xclip
    zsh        # needed for chsh (login shell)
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
# HOMEBREW INSTALLATION
# ============================================================================

install_homebrew() {
    log_header "Installing Homebrew"
    
    if command_exists brew; then
        log_success "Homebrew already installed"
        return
    fi
    
    log_info "Installing Homebrew (Linuxbrew)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >> "$LOG_FILE" 2>&1
    
    # Add to PATH for this session
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    
    if command_exists brew; then
        log_success "Homebrew installed"
    else
        log_error "Homebrew installation failed"
        exit 1
    fi
}

# ============================================================================
# HOMEBREW PACKAGES
# ============================================================================

install_brew_packages() {
    log_header "Installing Homebrew Packages"
    
    # Ensure brew is in PATH
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" 2>/dev/null
    
    for pkg in "${BREW_PACKAGES[@]}"; do
        if brew list "$pkg" &>/dev/null; then
            log_success "$pkg (already installed)"
        else
            log_info "Installing $pkg..."
            if brew install "$pkg" >> "$LOG_FILE" 2>&1; then
                log_success "$pkg installed"
            else
                log_warning "Failed to install $pkg"
            fi
        fi
    done
    
    # Install packages from taps
    for pkg in "${BREW_TAP_PACKAGES[@]}"; do
        local pkg_name="${pkg##*/}"  # Get package name after last /
        if brew list "$pkg_name" &>/dev/null; then
            log_success "$pkg_name (already installed)"
        else
            log_info "Installing $pkg..."
            if brew install "$pkg" >> "$LOG_FILE" 2>&1; then
                log_success "$pkg_name installed"
            else
                log_warning "Failed to install $pkg_name"
            fi
        fi
    done
}

# ============================================================================
# APT PACKAGES (minimal - just build deps)
# ============================================================================

install_apt_packages() {
    log_header "Installing APT Prerequisites"
    
    log_info "Updating package lists..."
    sudo apt update >> "$LOG_FILE" 2>&1
    
    local to_install=()
    
    for pkg in "${APT_PACKAGES[@]}"; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            log_success "$pkg (already installed)"
        else
            to_install+=("$pkg")
        fi
    done
    
    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "Installing ${#to_install[@]} packages..."
        if sudo apt install -y "${to_install[@]}" >> "$LOG_FILE" 2>&1; then
            log_success "APT packages installed"
        else
            log_warning "Some APT packages may have failed"
        fi
    fi
}

# ============================================================================
# GIT CONFIG
# ============================================================================

setup_git_config() {
    log_header "Setting up Git Configuration"
    
    if git config --global user.email &>/dev/null; then
        log_success "Git already configured: $(git config --global user.name) <$(git config --global user.email)>"
    else
        log_info "Configuring git..."
        read -p "Enter your Git email: " git_email
        read -p "Enter your Git name: " git_name
        git config --global user.email "$git_email"
        git config --global user.name "$git_name"
        log_success "Git configured"
    fi
}

# ============================================================================
# SSH KEY SETUP
# ============================================================================

setup_ssh_key() {
    log_header "Setting up SSH Key"
    
    local ssh_key="$HOME/.ssh/id_ed25519"
    local key_created=false
    
    if [ -f "$ssh_key" ]; then
        log_success "SSH key already exists at $ssh_key"
    else
        log_info "Generating SSH key..."
        mkdir -p "$HOME/.ssh"
        chmod 700 "$HOME/.ssh"
        
        # Use git email if configured
        local ssh_email
        if git config --global user.email &>/dev/null; then
            ssh_email=$(git config --global user.email)
            log_info "Using git email: $ssh_email"
        else
            ssh_email="user@$(hostname)"
            log_info "Using default email: $ssh_email"
        fi
        
        ssh-keygen -t ed25519 -C "$ssh_email" -f "$ssh_key" -N ""
        chmod 600 "$ssh_key"
        chmod 644 "${ssh_key}.pub"
        
        log_success "SSH key generated"
        key_created=true
    fi
    
    # Try to add to GitHub if gh is available and authenticated
    if command_exists gh; then
        local key_fingerprint=$(ssh-keygen -lf "${ssh_key}.pub" 2>/dev/null | awk '{print $2}')
        
        if gh ssh-key list 2>/dev/null | grep -q "$key_fingerprint"; then
            log_success "SSH key already on GitHub"
        elif gh auth status &>/dev/null; then
            # Already authenticated - add automatically
            log_info "Adding SSH key to GitHub..."
            if gh ssh-key add "${ssh_key}.pub" --title "WSL $(hostname)" 2>> "$LOG_FILE"; then
                log_success "SSH key added to GitHub"
            else
                log_warning "Failed to add SSH key to GitHub"
                log_info "Add manually: https://github.com/settings/keys"
                echo ""
                cat "${ssh_key}.pub"
                echo ""
            fi
        else
            # Not authenticated - show key and instructions
            log_info "GitHub CLI not authenticated"
            log_info "Add this SSH key manually at https://github.com/settings/keys"
            echo ""
            cat "${ssh_key}.pub"
            echo ""
        fi
    else
        log_info "Install gh (GitHub CLI) to auto-add SSH key, or add manually:"
        log_info "https://github.com/settings/keys"
        echo ""
        cat "${ssh_key}.pub"
        echo ""
    fi
}

# ============================================================================
# CHEZMOI SETUP
# ============================================================================

apply_dotfiles() {
    log_header "Applying Dotfiles with chezmoi"
    
    # Ensure brew's chezmoi is in PATH
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" 2>/dev/null
    
    if [ -f "$HOME/.zshrc" ] && chezmoi verify &>/dev/null 2>&1; then
        log_success "Dotfiles already applied"
    else
        log_info "Initializing and applying dotfiles..."
        chezmoi init --apply git@github.com:vitusli/dotfiles.git 2>&1 | tee -a "$LOG_FILE"
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
        if chsh -s "$(which zsh)" 2>> "$LOG_FILE"; then
            log_success "Default shell changed to zsh"
            log_info "Please log out and back in for the change to take effect"
        else
            log_warning "chsh failed - run manually: chsh -s $(which zsh)"
        fi
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
# Ensure WSL interop is enabled (allows running .exe from WSL)
        if [ ! -f /etc/wsl.conf ] || ! grep -q "enabled.*=.*true" /etc/wsl.conf 2>/dev/null; then
            log_info "Enabling WSL interop..."
            sudo tee /etc/wsl.conf > /dev/null << 'EOF'
[interop]
enabled = true
appendWindowsPath = true
EOF
            log_success "WSL interop configured (restart WSL for changes: wsl --shutdown)"
        else
            log_success "WSL interop already enabled"
        fi
        
        
        # Ensure WSL interop is enabled in config
        if [ ! -f /etc/wsl.conf ] || ! grep -q "\[interop\]" /etc/wsl.conf 2>/dev/null; then
            log_info "Configuring WSL interop..."
            sudo tee -a /etc/wsl.conf > /dev/null << 'EOF'

[interop]
enabled = true
appendWindowsPath = true
EOF
            log_success "WSL interop configured"
        fi
        
        # Register WSLInterop in binfmt_misc if missing (allows running .exe from WSL)
        if [ ! -f /proc/sys/fs/binfmt_misc/WSLInterop ]; then
            log_info "Registering WSL interop for Windows exe support..."
            sudo bash -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register' 2>/dev/null
            if [ -f /proc/sys/fs/binfmt_misc/WSLInterop ]; then
                log_success "WSL interop registered"
            else
                log_warning "Could not register WSL interop - restart WSL with 'wsl --shutdown'"
            fi
        else
            log_success "WSL interop already active"
        fi
        
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
    echo "  Linux/WSL Setup Script (Homebrew Edition)"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "This script will install:"
    echo "  - Homebrew (Linuxbrew)"
    echo "  - zsh with plugins (autosuggestions, syntax-highlighting, abbr)"
    echo "  - fzf, bat, lazygit, lf, zoxide and other CLI tools"
    echo "  - GitHub CLI (gh) for authentication"
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
    install_apt_packages    # Minimal: build-essential, curl, git, xclip
    install_homebrew        # The package manager
    install_brew_packages   # All the good stuff
    setup_git_config
    setup_ssh_key
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

