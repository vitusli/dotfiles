#!/bin/bash
# ============================================================================
# MACOS DUTI (DEFAULT APPS) MODULE
# Handles setting default applications for file types and URL schemes
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# DUTI VERIFICATION
# ============================================================================

# Check if duti is installed
verify_duti_installed() {
    command -v duti &>/dev/null
}

# Check if defaultbrowser is installed (for browser defaults)
verify_defaultbrowser_installed() {
    command -v defaultbrowser &>/dev/null
}

# Get current default app for a UTI
get_default_app_for_uti() {
    local uti="$1"
    local role="${2:-all}"

    if ! verify_duti_installed; then
        return 1
    fi

    duti -x "$uti" 2>/dev/null | head -1
}

# Get current default handler bundle ID for a UTI
get_default_handler_for_uti() {
    local uti="$1"
    local role="${2:-all}"

    if ! verify_duti_installed; then
        return 1
    fi

    # duti -d returns the bundle identifier
    duti -d "$uti" 2>/dev/null
}

# Verify a specific handler is set for a UTI
verify_handler_set() {
    local bundle_id="$1"
    local uti="$2"

    local current_handler
    current_handler=$(get_default_handler_for_uti "$uti")

    [[ "$current_handler" == "$bundle_id" ]]
}

# ============================================================================
# DUTI INSTALLATION
# ============================================================================

# Install duti
install_duti() {
    log_header "Installing duti"

    if verify_duti_installed; then
        log_success "duti already installed"
        return 0
    fi

    log_info "Installing duti..."

    if command -v brew &>/dev/null; then
        brew install duti >> "$LOG_FILE" 2>&1
    else
        log_error "Homebrew not installed - cannot install duti"
        return 1
    fi

    # Verify installation
    if verify_duti_installed; then
        log_success "duti installed"
        return 0
    else
        log_error "duti installation failed"
        return 1
    fi
}

# Install defaultbrowser
install_defaultbrowser() {
    log_info "Checking defaultbrowser..."

    if verify_defaultbrowser_installed; then
        log_success "defaultbrowser already installed"
        return 0
    fi

    log_info "Installing defaultbrowser..."

    if command -v brew &>/dev/null; then
        brew install defaultbrowser >> "$LOG_FILE" 2>&1
    else
        log_warning "Homebrew not installed - cannot install defaultbrowser"
        return 1
    fi

    if verify_defaultbrowser_installed; then
        log_success "defaultbrowser installed"
        return 0
    else
        log_warning "defaultbrowser installation failed"
        return 1
    fi
}

# ============================================================================
# DEFAULT APP SETTING
# ============================================================================

# Set default handler for a UTI
# Usage: set_default_handler "com.apple.Safari" "public.html" "viewer"
set_default_handler() {
    local bundle_id="$1"
    local uti="$2"
    local role="${3:-all}"

    if ! verify_duti_installed; then
        log_error "duti not installed"
        return 1
    fi

    # Check if already set correctly
    if verify_handler_set "$bundle_id" "$uti"; then
        log_success "$uti → $bundle_id (already set)"
        return 0
    fi

    log_info "Setting $uti → $bundle_id ($role)"

    # Use duti to set the handler
    # Format: bundle_id UTI role
    echo -e "${bundle_id}\t${uti}\t${role}" | duti >> "$LOG_FILE" 2>&1
    local exit_code=$?

    # Verify the change
    if verify_handler_set "$bundle_id" "$uti"; then
        log_success "$uti → $bundle_id"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        # duti reported success but we can't verify
        log_success "$uti → $bundle_id (command succeeded)"
        return 0
    else
        log_warning "Failed to set $uti → $bundle_id"
        return 1
    fi
}

# Set default browser
# Usage: set_default_browser "zen" or set_default_browser "firefox"
set_default_browser() {
    local browser="$1"

    log_info "Setting default browser to $browser..."

    if verify_defaultbrowser_installed; then
        defaultbrowser "$browser" >> "$LOG_FILE" 2>&1
        log_success "Default browser set to $browser"
        log_info "Note: macOS may show a confirmation dialog"
        return 0
    else
        log_warning "defaultbrowser not installed - cannot set default browser"
        return 1
    fi
}

# ============================================================================
# CONFIG-BASED SETUP
# ============================================================================

# Apply default apps from config file
# Config format: bundle_id|uti|role
# Example: com.microsoft.VSCode|public.python-script|editor
setup_default_apps() {
    log_header "Setting up Default Applications"

    if ! verify_duti_installed; then
        log_error "duti not found. Install duti first."
        return 1
    fi

    log_info "Loading duti config..."

    local duti_configs=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && duti_configs+=("$line")
    done < <(load_config "macos-duti.txt")

    if [[ ${#duti_configs[@]} -eq 0 ]]; then
        log_info "No duti configurations defined in config"
        return 0
    fi

    local success=0
    local failed=0

    for config in "${duti_configs[@]}"; do
        # Parse config: bundle_id|uti|role
        local bundle_id="${config%%|*}"
        local rest="${config#*|}"
        local uti="${rest%|*}"
        local role="${rest##*|}"

        # Default role to "all" if not specified or same as uti
        [[ "$role" == "$uti" || -z "$role" ]] && role="all"

        if set_default_handler "$bundle_id" "$uti" "$role"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    # Summary
    if [[ $failed -gt 0 ]]; then
        log_warning "Set $success handlers, $failed failed"
        return 1
    else
        log_success "All $success default handlers configured"
        return 0
    fi
}

# ============================================================================
# COMMON DEFAULT APPS
# ============================================================================

# Set VS Code as default for code files
setup_vscode_defaults() {
    log_info "Setting VS Code as default for code files..."

    local code_utis=(
        "public.plain-text"
        "public.python-script"
        "public.shell-script"
        "public.json"
        "public.yaml"
        "com.netscape.javascript-source"
        "public.ruby-script"
        "dyn.ah62d4rv4ge8003dcta"  # .md files
    )

    local bundle_id="com.microsoft.VSCode"

    for uti in "${code_utis[@]}"; do
        set_default_handler "$bundle_id" "$uti" "editor"
    done
}

# Set VLC as default for media files
setup_vlc_defaults() {
    log_info "Setting VLC as default for media files..."

    local media_utis=(
        "public.movie"
        "public.audio"
        "public.mp3"
        "public.mpeg-4"
        "public.avi"
        "com.apple.quicktime-movie"
    )

    local bundle_id="org.videolan.vlc"

    for uti in "${media_utis[@]}"; do
        set_default_handler "$bundle_id" "$uti" "viewer"
    done
}

# Set Marta as default folder handler
setup_marta_defaults() {
    log_info "Setting Marta as default folder handler..."

    set_default_handler "org.yanex.marta" "public.folder" "all"
}

# ============================================================================
# STATUS
# ============================================================================

# Show current default apps status
get_duti_status() {
    log_header "Default Applications Status"

    if verify_duti_installed; then
        log_success "duti: installed"
    else
        log_error "duti: not installed"
        return
    fi

    if verify_defaultbrowser_installed; then
        log_success "defaultbrowser: installed"
    else
        log_info "defaultbrowser: not installed"
    fi

    log_info ""
    log_info "Common file type handlers:"

    local common_utis=(
        "public.html:HTML files"
        "public.plain-text:Plain text"
        "public.json:JSON files"
        "public.folder:Folders"
        "public.movie:Video files"
        "public.audio:Audio files"
    )

    for item in "${common_utis[@]}"; do
        local uti="${item%%:*}"
        local description="${item#*:}"
        local handler
        handler=$(get_default_app_for_uti "$uti")

        if [[ -n "$handler" ]]; then
            log_info "  $description: $handler"
        else
            log_info "  $description: (system default)"
        fi
    done
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full duti setup
setup_duti() {
    local errors=0

    install_duti || ((errors++))
    install_defaultbrowser || true  # Optional, don't count as error

    setup_default_apps || ((errors++))

    if [[ $errors -gt 0 ]]; then
        log_warning "Default apps setup completed with $errors issues"
        return 1
    fi

    log_success "Default apps setup complete"
    return 0
}
