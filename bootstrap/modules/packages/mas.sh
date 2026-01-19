#!/bin/bash
# ============================================================================
# MAC APP STORE (MAS) MODULE
# Handles Mac App Store app installation via mas-cli
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# MAS VERIFICATION
# ============================================================================

# Check if mas is installed
verify_mas_installed() {
    command -v mas &>/dev/null
}

# Check if user is signed into App Store
verify_mas_signed_in() {
    if ! verify_mas_installed; then
        return 1
    fi
    # mas account returns non-zero if not signed in
    mas account &>/dev/null
}

# Get signed-in Apple ID
get_mas_account() {
    if verify_mas_signed_in; then
        mas account 2>/dev/null
    fi
}

# Check if a specific app is installed
verify_mas_app_installed() {
    local app_id="$1"
    if ! verify_mas_installed; then
        return 1
    fi
    mas list 2>/dev/null | grep -q "^${app_id}"
}

# Get installed app name by ID
get_mas_app_name() {
    local app_id="$1"
    mas list 2>/dev/null | grep "^${app_id}" | sed 's/^[0-9]* *//'
}

# ============================================================================
# MAS INSTALLATION
# ============================================================================

# Install mas-cli
install_mas() {
    log_header "Installing mas (Mac App Store CLI)"

    if verify_mas_installed; then
        log_success "mas already installed"
        return 0
    fi

    log_info "Installing mas..."

    if command -v brew &>/dev/null; then
        brew install mas >> "$LOG_FILE" 2>&1
    else
        log_error "Homebrew not installed - cannot install mas"
        return 1
    fi

    # Verify installation
    if verify_mas_installed; then
        log_success "mas installed"
        return 0
    else
        log_error "mas installation failed"
        return 1
    fi
}

# ============================================================================
# APP STORE AUTHENTICATION
# ============================================================================

# Check App Store sign-in status
check_mas_signin() {
    log_info "Checking App Store sign-in status..."

    if verify_mas_signed_in; then
        local account
        account=$(get_mas_account)
        log_success "Signed in as: $account"
        return 0
    else
        log_warning "Not signed into App Store"
        log_info "Please sign in via App Store app before installing apps"
        return 1
    fi
}

# ============================================================================
# APP INSTALLATION
# ============================================================================

# Install a single app by ID
install_mas_app() {
    local app_id="$1"
    local app_name="${2:-App $app_id}"

    if ! verify_mas_installed; then
        log_error "mas not installed"
        return 1
    fi

    # Check if already installed
    if verify_mas_app_installed "$app_id"; then
        local installed_name
        installed_name=$(get_mas_app_name "$app_id")
        log_success "$installed_name (already installed)"
        return 0
    fi

    log_info "Installing $app_name..."
    mas install "$app_id" >> "$LOG_FILE" 2>&1
    local exit_code=$?

    # Verify installation
    if verify_mas_app_installed "$app_id"; then
        log_success "$app_name installed"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        # mas reported success but we can't verify
        log_success "$app_name install command completed"
        return 0
    else
        log_error "$app_name installation failed"
        return 1
    fi
}

# Install apps from config file
install_mas_apps() {
    log_header "Installing Mac App Store Apps"

    if ! verify_mas_installed; then
        log_error "mas not found. Install mas first."
        return 1
    fi

    if ! verify_mas_signed_in; then
        log_error "Not signed into App Store. Please sign in first."
        return 1
    fi

    log_info "Loading Mac App Store apps from config..."

    local mas_apps=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && mas_apps+=("$line")
    done < <(load_config "macos-mas.txt")

    if [[ ${#mas_apps[@]} -eq 0 ]]; then
        log_info "No Mac App Store apps defined in config"
        return 0
    fi

    local installed=0
    local failed=()

    for app_info in "${mas_apps[@]}"; do
        local app_id="${app_info%%|*}"
        local app_name="${app_info#*|}"

        # If no name provided, use ID
        [[ "$app_name" == "$app_id" ]] && app_name="App $app_id"

        if install_mas_app "$app_id" "$app_name"; then
            ((installed++))
        else
            failed+=("$app_name")
        fi
    done

    # Summary
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Installed $installed apps. Failed: ${failed[*]}"
        return 1
    else
        log_success "All $installed Mac App Store apps installed"
        return 0
    fi
}

# ============================================================================
# APP UPDATE
# ============================================================================

# Update all Mac App Store apps
update_mas_apps() {
    log_header "Updating Mac App Store Apps"

    if ! verify_mas_installed; then
        log_error "mas not installed"
        return 1
    fi

    log_info "Checking for updates..."

    local outdated
    outdated=$(mas outdated 2>/dev/null)

    if [[ -z "$outdated" ]]; then
        log_success "All apps are up to date"
        return 0
    fi

    log_info "Updates available:"
    echo "$outdated"

    log_info "Installing updates..."
    mas upgrade >> "$LOG_FILE" 2>&1

    # Check again
    outdated=$(mas outdated 2>/dev/null)
    if [[ -z "$outdated" ]]; then
        log_success "All updates installed"
        return 0
    else
        log_warning "Some updates may have failed"
        return 1
    fi
}

# ============================================================================
# APP LISTING
# ============================================================================

# List all installed Mac App Store apps
list_mas_apps() {
    log_header "Installed Mac App Store Apps"

    if ! verify_mas_installed; then
        log_error "mas not installed"
        return 1
    fi

    mas list
}

# List outdated apps
list_mas_outdated() {
    log_header "Outdated Mac App Store Apps"

    if ! verify_mas_installed; then
        log_error "mas not installed"
        return 1
    fi

    local outdated
    outdated=$(mas outdated 2>/dev/null)

    if [[ -z "$outdated" ]]; then
        log_success "All apps are up to date"
    else
        echo "$outdated"
    fi
}

# ============================================================================
# STATUS
# ============================================================================

# Show mas status
get_mas_status() {
    log_header "Mac App Store Status"

    if verify_mas_installed; then
        log_success "mas: installed"
    else
        log_error "mas: not installed"
        return
    fi

    if verify_mas_signed_in; then
        local account
        account=$(get_mas_account)
        log_success "Signed in as: $account"
    else
        log_warning "Not signed into App Store"
    fi

    # Count installed apps
    local app_count
    app_count=$(mas list 2>/dev/null | wc -l | tr -d ' ')
    log_info "Installed App Store apps: $app_count"

    # Check for updates
    local outdated_count
    outdated_count=$(mas outdated 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$outdated_count" -eq 0 ]]; then
        log_success "All apps up to date"
    else
        log_warning "$outdated_count apps have updates available"
    fi
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full mas setup
setup_mas() {
    local errors=0

    install_mas || ((errors++))
    check_mas_signin || ((errors++))

    if [[ $errors -eq 0 ]]; then
        install_mas_apps || ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        log_warning "Mac App Store setup completed with $errors issues"
        return 1
    fi

    log_success "Mac App Store setup complete"
    return 0
}
