#!/bin/bash
# ============================================================================
# VS CODE EXTENSIONS MODULE
# Handles VS Code extension installation (cross-platform)
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# VS CODE VERIFICATION
# ============================================================================

# Check if VS Code CLI is available
verify_vscode_installed() {
    command -v code &>/dev/null
}

# Get VS Code version
get_vscode_version() {
    if verify_vscode_installed; then
        code --version 2>/dev/null | head -1
    fi
}

# Check if a specific extension is installed
verify_extension_installed() {
    local extension="$1"

    if ! verify_vscode_installed; then
        return 1
    fi

    # Case-insensitive check
    code --list-extensions 2>/dev/null | grep -qi "^${extension}$"
}

# Get list of installed extensions
get_installed_extensions() {
    if verify_vscode_installed; then
        code --list-extensions 2>/dev/null
    fi
}

# Count installed extensions
get_extension_count() {
    if verify_vscode_installed; then
        code --list-extensions 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# ============================================================================
# EXTENSION INSTALLATION
# ============================================================================

# Install a single extension
install_extension() {
    local extension="$1"

    if ! verify_vscode_installed; then
        log_error "VS Code not installed"
        return 1
    fi

    # Check if already installed
    if verify_extension_installed "$extension"; then
        log_success "$extension (already installed)"
        return 0
    fi

    log_info "Installing $extension..."
    code --install-extension "$extension" --force >> "$LOG_FILE" 2>&1
    local exit_code=$?

    # Verify installation
    if verify_extension_installed "$extension"; then
        log_success "$extension installed"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        # Command succeeded but we can't verify (might need reload)
        log_success "$extension install command completed"
        return 0
    else
        log_error "$extension installation failed"
        return 1
    fi
}

# Install extensions from config file
install_vscode_extensions() {
    log_header "Installing VS Code Extensions"

    if ! verify_vscode_installed; then
        log_warning "VS Code not installed, skipping extensions"
        return 1
    fi

    log_info "VS Code version: $(get_vscode_version)"
    log_info "Loading extensions from config..."

    local extensions
    mapfile -t extensions < <(load_all "vscode.txt")

    if [[ ${#extensions[@]} -eq 0 ]]; then
        log_info "No extensions defined in config"
        return 0
    fi

    local to_install=()
    local already_installed=0
    local failed=()

    # First pass: check what's already installed
    for extension in "${extensions[@]}"; do
        [[ -z "$extension" ]] && continue

        if verify_extension_installed "$extension"; then
            log_success "$extension"
            ((already_installed++))
        else
            to_install+=("$extension")
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_info "All ${already_installed} extensions already installed"
        return 0
    fi

    log_info "Installing ${#to_install[@]} new extensions..."

    # Second pass: install missing extensions
    for extension in "${to_install[@]}"; do
        log_info "Installing $extension..."
        code --install-extension "$extension" --force >> "$LOG_FILE" 2>&1

        # Verify installation
        if verify_extension_installed "$extension"; then
            log_success "$extension installed"
        else
            log_error "$extension installation failed"
            failed+=("$extension")
        fi
    done

    # Summary
    local installed=$((${#to_install[@]} - ${#failed[@]}))
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Installed $installed/${#to_install[@]} extensions. Failed: ${failed[*]}"
        return 1
    else
        log_success "All extensions installed successfully"
        return 0
    fi
}

# ============================================================================
# EXTENSION REMOVAL
# ============================================================================

# Uninstall a single extension
uninstall_extension() {
    local extension="$1"

    if ! verify_vscode_installed; then
        log_error "VS Code not installed"
        return 1
    fi

    # Check if installed
    if ! verify_extension_installed "$extension"; then
        log_info "$extension not installed"
        return 0
    fi

    log_info "Uninstalling $extension..."
    code --uninstall-extension "$extension" >> "$LOG_FILE" 2>&1
    local exit_code=$?

    # Verify removal
    if ! verify_extension_installed "$extension"; then
        log_success "$extension uninstalled"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        log_success "$extension uninstall command completed"
        return 0
    else
        log_error "$extension uninstall failed"
        return 1
    fi
}

# ============================================================================
# EXTENSION SYNC
# ============================================================================

# Sync extensions: install missing, optionally remove unlisted
sync_extensions() {
    local remove_unlisted="${1:-false}"

    log_header "Syncing VS Code Extensions"

    if ! verify_vscode_installed; then
        log_warning "VS Code not installed"
        return 1
    fi

    log_info "Loading desired extensions from config..."

    local desired_extensions
    mapfile -t desired_extensions < <(load_all "vscode.txt")

    # Convert to lowercase for comparison
    local desired_lower=()
    for ext in "${desired_extensions[@]}"; do
        [[ -n "$ext" ]] && desired_lower+=("${ext,,}")
    done

    # Get installed extensions
    local installed_extensions
    mapfile -t installed_extensions < <(get_installed_extensions)

    local installed_lower=()
    for ext in "${installed_extensions[@]}"; do
        [[ -n "$ext" ]] && installed_lower+=("${ext,,}")
    done

    # Find extensions to install
    local to_install=()
    for ext in "${desired_lower[@]}"; do
        local found=false
        for installed in "${installed_lower[@]}"; do
            if [[ "$ext" == "$installed" ]]; then
                found=true
                break
            fi
        done
        if [[ "$found" == "false" ]]; then
            to_install+=("$ext")
        fi
    done

    # Find extensions to remove (if requested)
    local to_remove=()
    if [[ "$remove_unlisted" == "true" ]]; then
        for installed in "${installed_lower[@]}"; do
            local found=false
            for ext in "${desired_lower[@]}"; do
                if [[ "$installed" == "$ext" ]]; then
                    found=true
                    break
                fi
            done
            if [[ "$found" == "false" ]]; then
                to_remove+=("$installed")
            fi
        done
    fi

    # Install missing
    if [[ ${#to_install[@]} -gt 0 ]]; then
        log_info "Installing ${#to_install[@]} missing extensions..."
        for ext in "${to_install[@]}"; do
            install_extension "$ext"
        done
    else
        log_success "No extensions to install"
    fi

    # Remove unlisted
    if [[ ${#to_remove[@]} -gt 0 ]]; then
        log_warning "Extensions to remove (${#to_remove[@]}):"
        for ext in "${to_remove[@]}"; do
            echo "  - $ext"
        done

        echo ""
        read -r -p "Remove these extensions? (y/n) " confirm
        if [[ "$confirm" =~ ^[yY]$ ]]; then
            for ext in "${to_remove[@]}"; do
                uninstall_extension "$ext"
            done
        else
            log_info "Removal skipped by user"
        fi
    fi

    log_success "Extension sync complete"
}

# ============================================================================
# EXTENSION UPDATE
# ============================================================================

# Update all extensions
update_extensions() {
    log_header "Updating VS Code Extensions"

    if ! verify_vscode_installed; then
        log_warning "VS Code not installed"
        return 1
    fi

    log_info "Updating all extensions..."

    # VS Code doesn't have a direct update command, but installing with --force updates
    local extensions
    mapfile -t extensions < <(get_installed_extensions)

    local updated=0
    for extension in "${extensions[@]}"; do
        [[ -z "$extension" ]] && continue

        log_info "Updating $extension..."
        code --install-extension "$extension" --force >> "$LOG_FILE" 2>&1
        ((updated++))
    done

    log_success "Updated $updated extensions"
}

# ============================================================================
# EXTENSION EXPORT
# ============================================================================

# Export installed extensions to stdout (for config file)
export_extensions() {
    log_header "Exporting Installed Extensions"

    if ! verify_vscode_installed; then
        log_error "VS Code not installed"
        return 1
    fi

    log_info "Installed extensions:"
    echo ""
    get_installed_extensions
    echo ""

    local count
    count=$(get_extension_count)
    log_info "Total: $count extensions"
}

# ============================================================================
# STATUS
# ============================================================================

# Show VS Code extension status
get_vscode_status() {
    log_header "VS Code Extension Status"

    if verify_vscode_installed; then
        log_success "VS Code: installed ($(get_vscode_version))"
    else
        log_error "VS Code: not installed"
        return
    fi

    # Count installed
    local installed_count
    installed_count=$(get_extension_count)
    log_info "Installed extensions: $installed_count"

    # Compare with config
    local desired_extensions
    mapfile -t desired_extensions < <(load_all "vscode.txt")
    local desired_count=${#desired_extensions[@]}

    log_info "Desired extensions (from config): $desired_count"

    # Find differences
    local missing=0
    for ext in "${desired_extensions[@]}"; do
        [[ -z "$ext" ]] && continue
        if ! verify_extension_installed "$ext"; then
            ((missing++))
        fi
    done

    if [[ $missing -eq 0 ]]; then
        log_success "All desired extensions are installed"
    else
        log_warning "$missing extensions from config are not installed"
    fi
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full VS Code extensions setup
setup_vscode_extensions() {
    local errors=0

    if ! verify_vscode_installed; then
        log_warning "VS Code not installed, skipping extensions"
        return 0
    fi

    install_vscode_extensions || ((errors++))

    if [[ $errors -gt 0 ]]; then
        log_warning "VS Code extensions setup completed with issues"
        return 1
    fi

    log_success "VS Code extensions setup complete"
    return 0
}
