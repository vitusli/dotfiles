#!/bin/bash

# Download and run with bash:
# curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linuxme.sh | bash

# Don't use set -e because some commands may fail non-fatally
set +e

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
        if sudo apt install -y "${to_install[@]}" >> "$LOG_FILE" 2>&1; then
            log_success "APT packages installed"
        else
            log_warning "Some APT packages may have failed - check log"
        fi
    else
        log_info "All required packages already installed"
    fi
}

# ============================================================================
# LF FILE MANAGER (not in Ubuntu repos, install via Go)
# ============================================================================

install_lf() {
    log_header "Installing lf file manager"
    
    if command_exists lf; then
        log_success "lf already installed"
        return
    fi
    
    # Try snap first (easiest)
    if command_exists snap; then
        log_info "Installing lf via snap..."
        if sudo snap install lf-fm 2>> "$LOG_FILE"; then
            log_success "lf installed via snap"
            return
        fi
    fi
    
    # Fallback: download binary from GitHub releases
    log_info "Installing lf from GitHub releases..."
    local lf_version="r32"
    local lf_url="https://github.com/gokcehan/lf/releases/download/${lf_version}/lf-linux-amd64.tar.gz"
    
    # Ensure ~/.local/bin exists
    mkdir -p ~/.local/bin
    
    if curl -fsSL "$lf_url" | tar -xz -C ~/.local/bin 2>> "$LOG_FILE"; then
        chmod +x ~/.local/bin/lf
        log_success "lf installed to ~/.local/bin"
    else
        log_warning "Failed to install lf - skipping"
    fi
}

# ============================================================================
# LAZYGIT (not in Ubuntu repos)
# ============================================================================

install_lazygit() {
    log_header "Installing lazygit"
    
    if command_exists lazygit; then
        log_success "lazygit already installed"
        return
    fi
    
    # Try PPA first (Ubuntu only, gets auto-updates)
    if command_exists add-apt-repository; then
        log_info "Adding lazygit PPA..."
        if sudo add-apt-repository -y ppa:lazygit-team/release >> "$LOG_FILE" 2>&1 && \
           sudo apt update >> "$LOG_FILE" 2>&1 && \
           sudo apt install -y lazygit >> "$LOG_FILE" 2>&1; then
            log_success "lazygit installed via PPA"
            return
        fi
    fi
    
    # Fallback: GitHub releases
    log_info "Installing lazygit from GitHub releases..."
    local lg_version="0.44.1"
    local lg_url="https://github.com/jesseduffield/lazygit/releases/download/v${lg_version}/lazygit_${lg_version}_Linux_x86_64.tar.gz"
    
    mkdir -p ~/.local/bin
    
    if curl -fsSL "$lg_url" | tar -xz -C ~/.local/bin lazygit 2>> "$LOG_FILE"; then
        chmod +x ~/.local/bin/lazygit
        log_success "lazygit installed to ~/.local/bin"
    else
        log_warning "Failed to install lazygit - skipping"
    fi
}

# ============================================================================
# GITHUB CLI (gh)
# ============================================================================

install_gh() {
    log_header "Installing GitHub CLI (gh)"
    
    if command_exists gh; then
        log_success "gh already installed"
        return
    fi
    
    log_info "Adding GitHub CLI repository (official method)..."
    
    # Official Debian/Ubuntu installation method
    if (type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
        && sudo mkdir -p -m 755 /etc/apt/keyrings \
        && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
        && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && sudo apt update >> "$LOG_FILE" 2>&1 \
        && sudo apt install -y gh >> "$LOG_FILE" 2>&1; then
        log_success "gh installed"
    else
        log_warning "Failed to install gh - skipping"
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
    
    if [ -f "$ssh_key" ]; then
        log_success "SSH key already exists"
    else
        log_info "Generating SSH key..."
        mkdir -p "$HOME/.ssh"
        chmod 700 "$HOME/.ssh"
        
        # Use git email if configured, otherwise ask
        local ssh_email
        if git config --global user.email &>/dev/null; then
            ssh_email=$(git config --global user.email)
            log_info "Using git email: $ssh_email"
        else
            read -p "Enter your email for SSH key: " ssh_email
        fi
        
        ssh-keygen -t ed25519 -C "$ssh_email" -f "$ssh_key" -N ""
        chmod 600 "$ssh_key"
        chmod 644 "${ssh_key}.pub"
        
        log_success "SSH key generated"
    fi
    
    # Always offer to add to GitHub if not already there
    if command_exists gh; then
        # Check if key is already on GitHub
        local key_fingerprint=$(ssh-keygen -lf "${ssh_key}.pub" 2>/dev/null | awk '{print $2}')
        
        if gh ssh-key list 2>/dev/null | grep -q "$key_fingerprint"; then
            log_success "SSH key already on GitHub"
        else
            log_info "Adding SSH key to GitHub..."
            echo ""
            cat "${ssh_key}.pub"
            echo ""
            
            read -p "Add this key to GitHub now? (y/n): " add_gh
            if [[ "$add_gh" =~ ^[yY]$ ]]; then
                if ! gh auth status &>/dev/null; then
                    log_info "Authenticating with GitHub..."
                    gh auth login
                fi
                gh ssh-key add "${ssh_key}.pub" --title "WSL $(hostname)"
                log_success "SSH key added to GitHub"
            else
                log_info "Skipped - add manually at https://github.com/settings/keys"
            fi
        fi
    fi
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
    echo "  - fzf, bat, lazygit, lf and other CLI tools"
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
    install_apt_packages
    install_lf
    install_lazygit
    install_gh
    setup_git_config
    setup_ssh_key
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

