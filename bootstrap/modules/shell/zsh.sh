#!/bin/bash
# ============================================================================
# ZSH SHELL MODULE
# Handles zsh installation and configuration as default shell
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"

# ============================================================================
# ZSH VERIFICATION
# ============================================================================

# Check if zsh is installed
verify_zsh_installed() {
    command -v zsh &>/dev/null
}

# Get zsh path
get_zsh_path() {
    which zsh 2>/dev/null
}

# Check if zsh is the default shell for current user
verify_zsh_is_default() {
    local current_shell
    current_shell=$(grep "^$(whoami):" /etc/passwd 2>/dev/null | cut -d: -f7)

    # Also check $SHELL environment variable
    if [[ "$current_shell" == *"zsh"* ]] || [[ "$SHELL" == *"zsh"* ]]; then
        return 0
    fi
    return 1
}

# Check if zsh is in /etc/shells
verify_zsh_in_shells() {
    local zsh_path
    zsh_path=$(get_zsh_path)

    if [[ -z "$zsh_path" ]]; then
        return 1
    fi

    grep -q "^${zsh_path}$" /etc/shells 2>/dev/null
}

# Get current default shell
get_current_shell() {
    grep "^$(whoami):" /etc/passwd 2>/dev/null | cut -d: -f7
}

# ============================================================================
# ZSH INSTALLATION
# ============================================================================

# Install zsh (platform-specific)
install_zsh() {
    log_header "Installing zsh"

    if verify_zsh_installed; then
        local version
        version=$(zsh --version 2>/dev/null | head -1)
        log_success "zsh already installed ($version)"
        return 0
    fi

    log_info "Installing zsh..."

    local os
    os=$(detect_os)

    case "$os" in
        linux)
            # Try pacman first (Arch)
            if command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm zsh >> "$LOG_FILE" 2>&1
            # Try apt (Debian/Ubuntu)
            elif command -v apt &>/dev/null; then
                sudo apt install -y zsh >> "$LOG_FILE" 2>&1
            # Try dnf (Fedora)
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y zsh >> "$LOG_FILE" 2>&1
            else
                log_error "No supported package manager found"
                return 1
            fi
            ;;
        macos)
            # zsh is preinstalled on modern macOS, but can be upgraded via brew
            if command -v brew &>/dev/null; then
                brew install zsh >> "$LOG_FILE" 2>&1
            else
                log_info "Using system zsh (brew not available)"
            fi
            ;;
        *)
            log_error "Unsupported OS: $os"
            return 1
            ;;
    esac

    # Verify installation
    if verify_zsh_installed; then
        local version
        version=$(zsh --version 2>/dev/null | head -1)
        log_success "zsh installed ($version)"
        return 0
    else
        log_error "zsh installation failed"
        return 1
    fi
}

# ============================================================================
# DEFAULT SHELL SETUP
# ============================================================================

# Add zsh to /etc/shells if not present
add_zsh_to_shells() {
    local zsh_path
    zsh_path=$(get_zsh_path)

    if [[ -z "$zsh_path" ]]; then
        log_error "zsh not found"
        return 1
    fi

    if verify_zsh_in_shells; then
        log_success "zsh already in /etc/shells"
        return 0
    fi

    log_info "Adding zsh to /etc/shells..."
    echo "$zsh_path" | sudo tee -a /etc/shells > /dev/null

    # Verify it was added
    if verify_zsh_in_shells; then
        log_success "zsh added to /etc/shells"
        return 0
    else
        log_error "Failed to add zsh to /etc/shells"
        return 1
    fi
}

# Set zsh as default shell
setup_zsh_default() {
    log_header "Setting zsh as Default Shell"

    if ! verify_zsh_installed; then
        log_error "zsh not installed"
        return 1
    fi

    local zsh_path
    zsh_path=$(get_zsh_path)

    # Check if already default
    if verify_zsh_is_default; then
        log_success "zsh is already the default shell"
        return 0
    fi

    local current_shell
    current_shell=$(get_current_shell)
    log_info "Current shell: $current_shell"
    log_info "Changing default shell to: $zsh_path"

    # Ensure zsh is in /etc/shells
    add_zsh_to_shells || return 1

    # Change shell
    chsh -s "$zsh_path" 2>> "$LOG_FILE"
    local exit_code=$?

    # Verify the change
    # Note: We need to check /etc/passwd directly since $SHELL won't update until re-login
    local new_shell
    new_shell=$(grep "^$(whoami):" /etc/passwd 2>/dev/null | cut -d: -f7)

    if [[ "$new_shell" == "$zsh_path" ]]; then
        log_success "Default shell changed to zsh"
        log_info "Please log out and back in for the change to take effect"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        # chsh succeeded but we can't verify (might be using LDAP/NIS)
        log_success "chsh command succeeded"
        log_info "Please log out and back in for the change to take effect"
        return 0
    else
        log_error "Failed to change default shell (exit code: $exit_code)"
        log_info "Try running manually: chsh -s $zsh_path"
        return 1
    fi
}

# ============================================================================
# ZSH CONFIGURATION
# ============================================================================

# Check if .zshrc exists
verify_zshrc_exists() {
    [[ -f "$HOME/.zshrc" ]]
}

# Check if zsh plugins directory exists
verify_zsh_plugins() {
    [[ -d "$HOME/.zsh" ]]
}

# Create basic .zshrc if it doesn't exist
create_basic_zshrc() {
    if verify_zshrc_exists; then
        log_info ".zshrc already exists"
        return 0
    fi

    log_info "Creating basic .zshrc..."

    cat > "$HOME/.zshrc" << 'EOF'
# Basic zsh configuration
# This file will be replaced by chezmoi dotfiles

# Prompt
PROMPT='%1~ %# '

# History
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY

# Basic options
setopt AUTO_CD
setopt CORRECT

# Completion
autoload -Uz compinit && compinit
EOF

    if verify_zshrc_exists; then
        log_success "Basic .zshrc created"
        return 0
    else
        log_error "Failed to create .zshrc"
        return 1
    fi
}

# ============================================================================
# ZSH PLUGIN VERIFICATION
# ============================================================================

# Check if zsh-autosuggestions is available
verify_zsh_autosuggestions() {
    # Check common locations
    [[ -f /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]] || \
    [[ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] || \
    [[ -f "$HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh" ]]
}

# Check if zsh-syntax-highlighting is available
verify_zsh_syntax_highlighting() {
    # Check common locations
    [[ -f /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] || \
    [[ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] || \
    [[ -f "$HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]]
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full zsh setup
setup_zsh() {
    local errors=0

    install_zsh || ((errors++))
    setup_zsh_default || ((errors++))

    if [[ $errors -gt 0 ]]; then
        log_warning "zsh setup completed with $errors issues"
        return 1
    fi

    log_success "zsh setup complete"
    return 0
}

# ============================================================================
# STATUS
# ============================================================================

# Show zsh status
get_zsh_status() {
    log_header "Zsh Status"

    if verify_zsh_installed; then
        local version
        version=$(zsh --version 2>/dev/null | head -1)
        log_success "zsh installed: $version"
        log_info "zsh path: $(get_zsh_path)"
    else
        log_error "zsh not installed"
    fi

    if verify_zsh_is_default; then
        log_success "zsh is default shell"
    else
        log_warning "zsh is NOT default shell (current: $(get_current_shell))"
    fi

    if verify_zshrc_exists; then
        log_success ".zshrc exists"
    else
        log_warning ".zshrc does not exist"
    fi

    if verify_zsh_autosuggestions; then
        log_success "zsh-autosuggestions available"
    else
        log_info "zsh-autosuggestions not found"
    fi

    if verify_zsh_syntax_highlighting; then
        log_success "zsh-syntax-highlighting available"
    else
        log_info "zsh-syntax-highlighting not found"
    fi
}
