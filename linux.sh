#!/bin/bash

# Arch Linux Bootstrap Script
# ============================
# Download and run with:
# curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/arch.sh | bash

set +e  # Don't exit on errors

# ============================================================================
# CONFIGURATION
# ============================================================================
LOG_FILE="$HOME/dotfiles/arch-setup-$(date +%Y%m%d-%H%M%S).log"
CONFIG_URL="https://raw.githubusercontent.com/vitusli/dotfiles/main/config"

# ============================================================================
# CONFIG LOADING FUNCTIONS
# ============================================================================

# Load packages from remote config file for Linux
load_packages() {
    local file="$1"
    local url="${CONFIG_URL}/${file}"
    
    curl -fsSL "$url" 2>/dev/null | \
        grep -v '^#' | \
        grep -v '^$' | \
        awk '!/#/ || /#linux/' | \
        grep -v "^[^#]*#macos[[:space:]]*$" | \
        grep -v "^[^#]*#windows[[:space:]]*$" | \
        sed 's/ *#.*//'
}

# Load all packages (no platform filtering)
load_all() {
    local file="$1"
    local url="${CONFIG_URL}/${file}"
    
    curl -fsSL "$url" 2>/dev/null | \
        grep -v '^#' | \
        grep -v '^$' | \
        sed 's/ *#.*//'
}

# Load config preserving format
load_config() {
    local file="$1"
    local url="${CONFIG_URL}/${file}"
    
    curl -fsSL "$url" 2>/dev/null | \
        grep -v '^#' | \
        grep -v '^$'
}

# Arch-specific packages (not in shared config)
ARCH_SPECIFIC=(
    # Build essentials
    base-devel
    curl
    wget
    
    # Sway & Wayland
    sway
    swaylock
    waybar
    wofi
    mako
    xdg-desktop-portal-wlr
    
    # Audio
    pipewire
    wireplumber
    pipewire-pulse
    pipewire-alsa
    
    # Wayland utilities
    grim
    slurp
    wl-clipboard
    
    # System utilities
    polkit
    brightnessctl
    playerctl
    
    # Fonts
    ttf-dejavu
    ttf-liberation
    noto-fonts
    noto-fonts-emoji
    
    # Terminal
    foot
)

# NVIDIA packages
NVIDIA_PACKAGES=(
    nvidia
    nvidia-utils
    nvidia-settings
    libva-nvidia-driver
)

# AUR-only packages (not available in pacman)
AUR_ONLY=(
    ulauncher
    espanso-wayland
    ttf-nerd-fonts-symbols
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
# PACMAN PACKAGES
# ============================================================================

install_pacman_packages() {
    log_header "Installing Pacman Packages"
    
    log_info "Updating system..."
    sudo pacman -Syu --noconfirm >> "$LOG_FILE" 2>&1
    
    log_info "Loading packages from config..."
    local cli_packages=($(load_packages "cli.txt"))
    local gui_packages=($(load_packages "gui.txt"))
    
    # Combine with arch-specific packages
    local all_packages=("${ARCH_SPECIFIC[@]}" "${cli_packages[@]}" "${gui_packages[@]}")
    
    for pkg in "${all_packages[@]}"; do
        if pacman -Qi "$pkg" &>/dev/null; then
            log_success "$pkg (already installed)"
        elif pacman -Ss "^${pkg}$" &>/dev/null; then
            log_info "Installing $pkg..."
            if sudo pacman -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1; then
                log_success "$pkg installed"
            else
                log_warning "Failed to install $pkg (may be AUR)"
            fi
        else
            log_info "$pkg not in repos (will try AUR)"
        fi
    done
}

# ============================================================================
# NVIDIA DRIVER
# ============================================================================

install_nvidia() {
    log_header "Installing NVIDIA Driver"
    
    # Check if NVIDIA GPU present
    if ! lspci | grep -i nvidia &>/dev/null; then
        log_info "No NVIDIA GPU detected, skipping"
        return
    fi
    
    for pkg in "${NVIDIA_PACKAGES[@]}"; do
        if pacman -Qi "$pkg" &>/dev/null; then
            log_success "$pkg (already installed)"
        else
            log_info "Installing $pkg..."
            if sudo pacman -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1; then
                log_success "$pkg installed"
            else
                log_warning "Failed to install $pkg"
            fi
        fi
    done
    
    # Configure NVIDIA for Wayland
    log_info "Configuring NVIDIA for Wayland..."
    
    # Kernel parameter
    sudo mkdir -p /etc/modprobe.d
    echo "options nvidia_drm modeset=1 fbdev=1" | sudo tee /etc/modprobe.d/nvidia.conf > /dev/null
    
    # Environment variables for Sway
    sudo mkdir -p /etc/environment.d
    cat << 'EOF' | sudo tee /etc/environment.d/nvidia-wayland.conf > /dev/null
WLR_NO_HARDWARE_CURSORS=1
LIBVA_DRIVER_NAME=nvidia
GBM_BACKEND=nvidia-drm
__GLX_VENDOR_LIBRARY_NAME=nvidia
EOF
    
    # Rebuild initramfs
    log_info "Rebuilding initramfs..."
    sudo mkinitcpio -P >> "$LOG_FILE" 2>&1
    
    log_success "NVIDIA configured for Wayland"
    log_warning "Reboot required for NVIDIA changes to take effect"
}

# ============================================================================
# YAY (AUR HELPER)
# ============================================================================

install_yay() {
    log_header "Installing yay (AUR Helper)"
    
    if command_exists yay; then
        log_success "yay already installed"
        return
    fi
    
    log_info "Building yay from AUR..."
    local temp_dir=$(mktemp -d)
    git clone https://aur.archlinux.org/yay.git "$temp_dir/yay" >> "$LOG_FILE" 2>&1
    cd "$temp_dir/yay"
    makepkg -si --noconfirm >> "$LOG_FILE" 2>&1
    cd - > /dev/null
    rm -rf "$temp_dir"
    
    if command_exists yay; then
        log_success "yay installed"
    else
        log_error "yay installation failed"
    fi
}

# ============================================================================
# AUR PACKAGES
# ============================================================================

install_aur_packages() {
    log_header "Installing AUR Packages"
    
    if ! command_exists yay; then
        log_error "yay not available, skipping AUR packages"
        return
    fi
    
    log_info "Loading AUR packages from config..."
    local cli_packages=($(load_packages "cli.txt"))
    local gui_packages=($(load_packages "gui.txt"))
    
    # Combine config packages with AUR-only packages
    local all_aur=("${AUR_ONLY[@]}" "${cli_packages[@]}" "${gui_packages[@]}")
    
    for pkg in "${all_aur[@]}"; do
        if yay -Qi "$pkg" &>/dev/null; then
            log_success "$pkg (already installed)"
        elif ! pacman -Qi "$pkg" &>/dev/null; then
            # Only install via AUR if not already in pacman
            log_info "Installing $pkg from AUR..."
            if yay -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1; then
                log_success "$pkg installed"
            else
                log_warning "Failed to install $pkg"
            fi
        fi
    done
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
            if gh ssh-key add "${ssh_key}.pub" --title "Arch $(hostname)" 2>> "$LOG_FILE"; then
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
    
    if [ -f "$HOME/.zshrc" ] && chezmoi verify &>/dev/null 2>&1; then
        log_success "Dotfiles already applied"
    else
        log_info "Initializing and applying dotfiles..."
        chezmoi init --branch linux --apply vitusli/dotfiles 2>&1 | tee -a "$LOG_FILE"
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
# SERVICES
# ============================================================================

enable_services() {
    log_header "Enabling Services"
    
    # System services
    local system_services=(
        NetworkManager
    )
    
    for svc in "${system_services[@]}"; do
        if systemctl is-enabled "$svc" &>/dev/null; then
            log_success "$svc (already enabled)"
        else
            log_info "Enabling $svc..."
            sudo systemctl enable --now "$svc" >> "$LOG_FILE" 2>&1
            log_success "$svc enabled"
        fi
    done
    
    # User services (pipewire)
    local user_services=(
        pipewire
        wireplumber
        pipewire-pulse
    )
    
    for svc in "${user_services[@]}"; do
        if systemctl --user is-enabled "$svc" &>/dev/null; then
            log_success "$svc (user, already enabled)"
        else
            log_info "Enabling $svc (user)..."
            systemctl --user enable --now "$svc" >> "$LOG_FILE" 2>&1
            log_success "$svc enabled"
        fi
    done
}

# ============================================================================
# SWAY AUTOSTART
# ============================================================================

setup_sway_autostart() {
    log_header "Configuring Sway Autostart"
    
    local zprofile="$HOME/.zprofile"
    
    if [ -f "$zprofile" ] && grep -q "exec sway" "$zprofile"; then
        log_success "Sway autostart already configured"
    else
        log_info "Adding Sway autostart to .zprofile..."
        cat >> "$zprofile" << 'EOF'

# Start Sway on TTY1
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec sway
fi
EOF
        log_success "Sway autostart configured"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo "════════════════════════════════════════════════════════════"
    echo "  Arch Linux Setup Script"
    echo "  For Design/Dev Workflow with Sway + NVIDIA"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "This script will install:"
    echo "  - NVIDIA drivers (if GPU detected)"
    echo "  - Sway + Waybar + Wofi (Wayland desktop)"
    echo "  - Pipewire (audio)"
    echo "  - CLI tools (fzf, bat, lazygit, lf, zoxide, chezmoi)"
    echo "  - VS Code, Blender, Firefox (via AUR)"
    echo "  - Ulauncher, Espanso"
    echo "  - zsh with plugins"
    echo "  - Dotfiles via chezmoi"
    echo ""
    echo "Log file: $LOG_FILE"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to abort..."
    
    # Initialize log
    mkdir -p "$(dirname "$LOG_FILE")"
    {
        echo "════════════════════════════════════════════════════════════"
        echo "Arch Linux Setup Log"
        echo "Start: $(date)"
        echo "User: $(whoami)"
        echo "Host: $(hostname)"
        echo "════════════════════════════════════════════════════════════"
    } > "$LOG_FILE"
    
    # Run setup steps
    install_pacman_packages
    install_nvidia
    install_yay
    install_aur_packages
    setup_git_config
    setup_ssh_key
    apply_dotfiles
    enable_services
    setup_zsh_default
    setup_sway_autostart
    
    # Done
    log_header "Setup Complete!"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  ✓ Installation complete!"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. Reboot your system (required for NVIDIA)"
    echo "     sudo reboot"
    echo ""
    echo "  2. After reboot, Sway will start automatically on TTY1"
    echo "     Or start manually: sway"
    echo ""
    echo "  3. Open VS Code: code"
    echo "     Open Blender: blender"
    echo ""
    echo "Keybindings (Sway defaults):"
    echo "  Super+Enter     → Terminal"
    echo "  Super+D         → App launcher (wofi)"
    echo "  Super+Shift+Q   → Close window"
    echo "  Super+Shift+E   → Exit Sway"
    echo ""
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "End: $(date)" >> "$LOG_FILE"
}

main "$@"

