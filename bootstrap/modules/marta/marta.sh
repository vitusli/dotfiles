#!/bin/bash
# ============================================================================
# MARTA MODULE
# Handles Marta file manager setup for macOS
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"

# ============================================================================
# CONFIGURATION
# ============================================================================

MARTA_APP_PATH="${MARTA_APP_PATH:-/Applications/Marta.app}"
MARTA_LAUNCHER="${MARTA_APP_PATH}/Contents/Resources/launcher"
MARTA_SYMLINK="/usr/local/bin/marta"

# ============================================================================
# VERIFICATION
# ============================================================================

verify_marta_installed() {
    [[ -d "$MARTA_APP_PATH" ]]
}

verify_marta_launcher_exists() {
    [[ -f "$MARTA_LAUNCHER" ]]
}

verify_marta_symlink_exists() {
    [[ -L "$MARTA_SYMLINK" ]]
}

verify_marta_symlink_correct() {
    [[ -L "$MARTA_SYMLINK" ]] && [[ "$(readlink "$MARTA_SYMLINK")" == "$MARTA_LAUNCHER" ]]
}

# ============================================================================
# SETUP
# ============================================================================

create_marta_symlink() {
    log_info "Creating Marta launcher symlink..."

    # Ensure /usr/local/bin exists
    if [[ ! -d "/usr/local/bin" ]]; then
        sudo mkdir -p /usr/local/bin
    fi

    # Remove existing symlink if it points elsewhere
    if [[ -L "$MARTA_SYMLINK" ]] && ! verify_marta_symlink_correct; then
        sudo rm "$MARTA_SYMLINK"
    fi

    # Create symlink
    sudo ln -sf "$MARTA_LAUNCHER" "$MARTA_SYMLINK"

    if verify_marta_symlink_correct; then
        log_success "Marta launcher configured"
        return 0
    else
        log_error "Failed to create Marta symlink"
        return 1
    fi
}

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

setup_marta() {
    log_header "Configuring Marta"

    if ! verify_marta_installed; then
        log_warning "Marta.app not found at $MARTA_APP_PATH"
        return 1
    fi

    if ! verify_marta_launcher_exists; then
        log_warning "Marta launcher not found at $MARTA_LAUNCHER"
        return 1
    fi

    if verify_marta_symlink_correct; then
        log_success "Marta launcher symlink already exists"
        return 0
    fi

    create_marta_symlink
}

remove_marta_symlink() {
    log_header "Removing Marta Symlink"

    if ! verify_marta_symlink_exists; then
        log_info "Marta symlink does not exist"
        return 0
    fi

    sudo rm "$MARTA_SYMLINK"

    if ! verify_marta_symlink_exists; then
        log_success "Marta symlink removed"
        return 0
    else
        log_error "Failed to remove Marta symlink"
        return 1
    fi
}

get_marta_status() {
    log_header "Marta Status"

    if verify_marta_installed; then
        log_success "Marta installed: $MARTA_APP_PATH"
    else
        log_warning "Marta not installed"
        return
    fi

    if verify_marta_launcher_exists; then
        log_success "Marta launcher exists"
    else
        log_warning "Marta launcher not found"
    fi

    if verify_marta_symlink_correct; then
        log_success "Marta symlink configured: $MARTA_SYMLINK"
    elif verify_marta_symlink_exists; then
        log_warning "Marta symlink exists but points to wrong location"
    else
        log_warning "Marta symlink not configured"
    fi
}
