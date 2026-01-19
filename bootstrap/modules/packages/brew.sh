#!/bin/bash
# ============================================================================
# HOMEBREW PACKAGE MODULE
# Handles Homebrew installation, formulae, and casks for macOS
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# HOMEBREW INSTALLATION
# ============================================================================

# Check if Homebrew is installed
verify_brew_installed() {
    command -v brew &>/dev/null
}

# Install Homebrew
install_brew() {
    log_header "Setting up Homebrew"

    if verify_brew_installed; then
        log_success "Homebrew already installed"
        _setup_brew_environment
        return 0
    fi

    log_info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Verify installation
    if verify_brew_installed; then
        log_success "Homebrew installed"
        _setup_brew_environment
        return 0
    else
        log_error "Homebrew installation failed"
        return 1
    fi
}

# Setup Homebrew environment (add to PATH)
_setup_brew_environment() {
    local brew_prefix=""

    # Determine brew prefix based on architecture
    if [[ -f /opt/homebrew/bin/brew ]]; then
        brew_prefix="/opt/homebrew"
    elif [[ -f /usr/local/bin/brew ]]; then
        brew_prefix="/usr/local"
    fi

    if [[ -z "$brew_prefix" ]]; then
        log_warning "Could not determine Homebrew prefix"
        return 1
    fi

    # Add to current session
    eval "$($brew_prefix/bin/brew shellenv)"

    # Add to .zprofile if not already there
    local zprofile="$HOME/.zprofile"
    local shellenv_line="eval \"\$($brew_prefix/bin/brew shellenv)\""

    if ! grep -q 'brew shellenv' "$zprofile" 2>/dev/null; then
        log_info "Adding Homebrew to ~/.zprofile"
        echo "" >> "$zprofile"
        echo "$shellenv_line" >> "$zprofile"

        # Verify it was added
        if grep -q 'brew shellenv' "$zprofile"; then
            log_success "Homebrew environment configured"
        else
            log_warning "Failed to add Homebrew to .zprofile"
        fi
    else
        log_success "Homebrew already in ~/.zprofile"
    fi
}

# ============================================================================
# FORMULA VERIFICATION
# ============================================================================

# Check if a formula is installed
verify_formula_installed() {
    local formula="$1"
    brew list "$formula" &>/dev/null 2>&1
}

# Check if a cask is installed
verify_cask_installed() {
    local cask="$1"
    brew list --cask "$cask" &>/dev/null 2>&1
}

# Get installed formula version
get_formula_version() {
    local formula="$1"
    brew list --versions "$formula" 2>/dev/null | awk '{print $2}'
}

# ============================================================================
# FORMULA INSTALLATION
# ============================================================================

# Install formulae from config
install_formulae() {
    log_header "Installing Homebrew Formulae"

    if ! verify_brew_installed; then
        log_error "Homebrew not installed"
        return 1
    fi

    log_info "Loading CLI packages from config..."
    local formulae
    mapfile -t formulae < <(load_packages "cli.txt" "macos")

    # Add macOS-specific tools that are always needed
    formulae+=(duti mas)

    local to_install=()
    local already_installed=0
    local failed=()

    for formula in "${formulae[@]}"; do
        [[ -z "$formula" ]] && continue

        if verify_formula_installed "$formula"; then
            log_success "$formula ($(get_formula_version "$formula"))"
            ((already_installed++))
        else
            to_install+=("$formula")
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_info "All ${already_installed} formulae already installed"
        return 0
    fi

    log_info "Installing ${#to_install[@]} new formulae..."

    for formula in "${to_install[@]}"; do
        log_info "Installing $formula..."
        brew install "$formula" >> "$LOG_FILE" 2>&1

        # Verify installation
        if verify_formula_installed "$formula"; then
            log_success "$formula installed ($(get_formula_version "$formula"))"
        else
            log_error "$formula installation failed"
            failed+=("$formula")
        fi
    done

    # Summary
    local installed=$((${#to_install[@]} - ${#failed[@]}))
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Installed $installed/${#to_install[@]} formulae. Failed: ${failed[*]}"
        return 1
    else
        log_success "All formulae installed successfully"
        return 0
    fi
}

# ============================================================================
# CASK INSTALLATION
# ============================================================================

# Install casks from config
install_casks() {
    log_header "Installing Homebrew Casks"

    if ! verify_brew_installed; then
        log_error "Homebrew not installed"
        return 1
    fi

    log_info "Loading GUI apps from config..."
    local casks
    mapfile -t casks < <(load_packages "gui.txt" "macos")

    local to_install=()
    local already_installed=0
    local failed=()

    for cask in "${casks[@]}"; do
        [[ -z "$cask" ]] && continue

        if verify_cask_installed "$cask"; then
            log_success "$cask"
            ((already_installed++))
        else
            to_install+=("$cask")
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_info "All ${already_installed} casks already installed"
        return 0
    fi

    log_info "Installing ${#to_install[@]} new casks..."

    for cask in "${to_install[@]}"; do
        log_info "Installing $cask..."
        brew install --cask "$cask" >> "$LOG_FILE" 2>&1

        # Verify installation
        if verify_cask_installed "$cask"; then
            log_success "$cask installed"
        else
            log_error "$cask installation failed"
            failed+=("$cask")
        fi
    done

    # Summary
    local installed=$((${#to_install[@]} - ${#failed[@]}))
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Installed $installed/${#to_install[@]} casks. Failed: ${failed[*]}"
        return 1
    else
        log_success "All casks installed successfully"
        return 0
    fi
}

# ============================================================================
# CLEANUP
# ============================================================================

# Remove packages not in config
cleanup_brew() {
    log_header "Cleaning up Homebrew (removing unlisted packages)"

    if ! verify_brew_installed; then
        log_error "Homebrew not installed"
        return 1
    fi

    # Load desired packages from config
    log_info "Loading desired packages from config..."
    local desired_formulae
    mapfile -t desired_formulae < <(load_packages "cli.txt" "macos")
    desired_formulae+=(duti mas)

    local desired_casks
    mapfile -t desired_casks < <(load_packages "gui.txt" "macos")

    # Get leaf formulae (top-level, not dependencies)
    local leaf_formulae
    mapfile -t leaf_formulae < <(brew leaves 2>/dev/null)

    local installed_casks
    mapfile -t installed_casks < <(brew list --cask -1 2>/dev/null)

    # Find formulae to remove
    local formulae_to_remove=()
    for formula in "${leaf_formulae[@]}"; do
        if ! in_array "$formula" "${desired_formulae[@]}"; then
            formulae_to_remove+=("$formula")
        fi
    done

    # Find casks to remove
    local casks_to_remove=()
    for cask in "${installed_casks[@]}"; do
        if ! in_array "$cask" "${desired_casks[@]}"; then
            casks_to_remove+=("$cask")
        fi
    done

    # Report findings
    if [[ ${#formulae_to_remove[@]} -eq 0 ]] && [[ ${#casks_to_remove[@]} -eq 0 ]]; then
        log_success "No packages to remove - Homebrew is clean"
        return 0
    fi

    # Show what will be removed
    if [[ ${#formulae_to_remove[@]} -gt 0 ]]; then
        log_warning "Formulae to remove (${#formulae_to_remove[@]}):"
        for formula in "${formulae_to_remove[@]}"; do
            echo "  - $formula"
        done
    fi

    if [[ ${#casks_to_remove[@]} -gt 0 ]]; then
        log_warning "Casks to remove (${#casks_to_remove[@]}):"
        for cask in "${casks_to_remove[@]}"; do
            echo "  - $cask"
        done
    fi

    # Ask for confirmation
    echo ""
    read -r -p "Do you want to remove these packages? (y/n) " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        log_info "Cleanup skipped by user"
        return 0
    fi

    # Remove casks first
    for cask in "${casks_to_remove[@]}"; do
        log_info "Removing cask: $cask"
        brew uninstall --cask "$cask" >> "$LOG_FILE" 2>&1

        # Verify removal
        if ! verify_cask_installed "$cask"; then
            log_success "$cask removed"
        else
            log_warning "$cask removal failed"
        fi
    done

    # Remove formulae
    for formula in "${formulae_to_remove[@]}"; do
        log_info "Removing formula: $formula"
        brew uninstall "$formula" >> "$LOG_FILE" 2>&1

        # Verify removal
        if ! verify_formula_installed "$formula"; then
            log_success "$formula removed"
        else
            log_warning "$formula removal failed"
        fi
    done

    # Cleanup orphaned dependencies
    log_info "Running brew autoremove..."
    brew autoremove >> "$LOG_FILE" 2>&1

    log_info "Running brew cleanup..."
    brew cleanup >> "$LOG_FILE" 2>&1

    log_success "Homebrew cleanup complete"
}

# ============================================================================
# UPDATE
# ============================================================================

# Update Homebrew and all packages
update_brew() {
    log_header "Updating Homebrew"

    if ! verify_brew_installed; then
        log_error "Homebrew not installed"
        return 1
    fi

    log_info "Updating Homebrew..."
    brew update >> "$LOG_FILE" 2>&1

    log_info "Upgrading formulae..."
    brew upgrade >> "$LOG_FILE" 2>&1

    log_info "Upgrading casks..."
    brew upgrade --cask >> "$LOG_FILE" 2>&1

    log_success "Homebrew update complete"
}
