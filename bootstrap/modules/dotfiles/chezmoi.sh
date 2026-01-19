#!/bin/bash
# ============================================================================
# CHEZMOI DOTFILES MODULE
# Handles dotfiles management with chezmoi
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default dotfiles repository
DOTFILES_REPO="${DOTFILES_REPO:-vitusli/dotfiles}"
CHEZMOI_SOURCE="${CHEZMOI_SOURCE:-$HOME/.local/share/chezmoi}"

# ============================================================================
# CHEZMOI VERIFICATION
# ============================================================================

# Check if chezmoi is installed
verify_chezmoi_installed() {
    command -v chezmoi &>/dev/null
}

# Get chezmoi version
get_chezmoi_version() {
    chezmoi --version 2>/dev/null | head -1
}

# Check if chezmoi is initialized
verify_chezmoi_initialized() {
    [[ -d "$CHEZMOI_SOURCE/.git" ]]
}

# Get current chezmoi branch
get_chezmoi_branch() {
    if verify_chezmoi_initialized; then
        git -C "$CHEZMOI_SOURCE" rev-parse --abbrev-ref HEAD 2>/dev/null
    fi
}

# Check if dotfiles are applied (basic check for .zshrc)
verify_dotfiles_applied() {
    [[ -f "$HOME/.zshrc" ]] && chezmoi verify &>/dev/null 2>&1
}

# ============================================================================
# CHEZMOI INSTALLATION
# ============================================================================

# Install chezmoi
install_chezmoi() {
    log_header "Installing chezmoi"

    if verify_chezmoi_installed; then
        log_success "chezmoi already installed ($(get_chezmoi_version))"
        return 0
    fi

    log_info "Installing chezmoi..."

    local os
    os=$(detect_os)

    case "$os" in
        macos)
            if command -v brew &>/dev/null; then
                brew install chezmoi >> "$LOG_FILE" 2>&1
            else
                # Use official installer
                sh -c "$(curl -fsLS get.chezmoi.io)" >> "$LOG_FILE" 2>&1
            fi
            ;;
        linux)
            if command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm chezmoi >> "$LOG_FILE" 2>&1
            elif command -v apt &>/dev/null; then
                sudo apt install -y chezmoi >> "$LOG_FILE" 2>&1
            else
                # Use official installer
                sh -c "$(curl -fsLS get.chezmoi.io)" >> "$LOG_FILE" 2>&1
            fi
            ;;
        *)
            # Fallback to official installer
            sh -c "$(curl -fsLS get.chezmoi.io)" >> "$LOG_FILE" 2>&1
            ;;
    esac

    # Verify installation
    if verify_chezmoi_installed; then
        log_success "chezmoi installed ($(get_chezmoi_version))"
        return 0
    else
        log_error "chezmoi installation failed"
        return 1
    fi
}

# ============================================================================
# DOTFILES INITIALIZATION
# ============================================================================

# Initialize chezmoi with dotfiles repo
init_chezmoi() {
    local branch="${1:-}"
    local repo="${2:-$DOTFILES_REPO}"

    log_header "Initializing chezmoi"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    # Check if already initialized with correct branch
    if verify_chezmoi_initialized; then
        local current_branch
        current_branch=$(get_chezmoi_branch)

        if [[ -n "$branch" && "$current_branch" != "$branch" ]]; then
            log_info "Switching chezmoi to branch: $branch"
            git -C "$CHEZMOI_SOURCE" fetch origin "$branch" >> "$LOG_FILE" 2>&1
            git -C "$CHEZMOI_SOURCE" checkout "$branch" >> "$LOG_FILE" 2>&1

            # Verify branch switch
            current_branch=$(get_chezmoi_branch)
            if [[ "$current_branch" == "$branch" ]]; then
                log_success "Switched to branch: $branch"
            else
                log_warning "Failed to switch to branch: $branch (on: $current_branch)"
            fi
        else
            log_success "chezmoi already initialized (branch: $current_branch)"
        fi
        return 0
    fi

    log_info "Initializing chezmoi with $repo..."

    local init_cmd="chezmoi init"
    [[ -n "$branch" ]] && init_cmd+=" --branch $branch"
    init_cmd+=" $repo"

    eval "$init_cmd" >> "$LOG_FILE" 2>&1

    # Verify initialization
    if verify_chezmoi_initialized; then
        local current_branch
        current_branch=$(get_chezmoi_branch)
        log_success "chezmoi initialized (branch: $current_branch)"
        return 0
    else
        log_error "chezmoi initialization failed"
        return 1
    fi
}

# ============================================================================
# DOTFILES APPLICATION
# ============================================================================

# Apply dotfiles
apply_dotfiles() {
    log_header "Applying Dotfiles"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    if ! verify_chezmoi_initialized; then
        log_error "chezmoi not initialized. Run init_chezmoi first."
        return 1
    fi

    log_info "Applying dotfiles..."
    chezmoi apply --verbose >> "$LOG_FILE" 2>&1
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Dotfiles applied successfully"
        return 0
    else
        log_error "Dotfiles apply failed (exit code: $exit_code)"
        return 1
    fi
}

# Initialize and apply dotfiles in one step
init_and_apply_dotfiles() {
    local branch="${1:-}"
    local repo="${2:-$DOTFILES_REPO}"

    log_header "Applying Dotfiles with chezmoi"

    if ! verify_chezmoi_installed; then
        install_chezmoi || return 1
    fi

    # Check if already applied
    if verify_dotfiles_applied; then
        log_success "Dotfiles already applied"
        return 0
    fi

    log_info "Initializing and applying dotfiles..."

    local init_cmd="chezmoi init --apply"
    [[ -n "$branch" ]] && init_cmd+=" --branch $branch"
    init_cmd+=" $repo"

    eval "$init_cmd" 2>&1 | tee -a "$LOG_FILE"
    local exit_code=${PIPESTATUS[0]}

    # Verify application
    if [[ -f "$HOME/.zshrc" ]]; then
        log_success "Dotfiles applied successfully"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        log_success "chezmoi init --apply completed"
        return 0
    else
        log_error "Dotfiles application failed"
        return 1
    fi
}

# ============================================================================
# DOTFILES UPDATE
# ============================================================================

# Update dotfiles from remote
update_dotfiles() {
    log_header "Updating Dotfiles"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    if ! verify_chezmoi_initialized; then
        log_error "chezmoi not initialized"
        return 1
    fi

    log_info "Pulling latest changes..."
    chezmoi update --verbose >> "$LOG_FILE" 2>&1
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Dotfiles updated successfully"
        return 0
    else
        log_error "Dotfiles update failed (exit code: $exit_code)"
        return 1
    fi
}

# ============================================================================
# DOTFILES DIFF
# ============================================================================

# Show diff between source and destination
show_dotfiles_diff() {
    log_header "Dotfiles Diff"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    if ! verify_chezmoi_initialized; then
        log_error "chezmoi not initialized"
        return 1
    fi

    chezmoi diff
}

# ============================================================================
# DOTFILES VERIFICATION
# ============================================================================

# Verify all managed files are in sync
verify_dotfiles() {
    log_header "Verifying Dotfiles"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    if ! verify_chezmoi_initialized; then
        log_error "chezmoi not initialized"
        return 1
    fi

    log_info "Checking for differences..."

    local diff_output
    diff_output=$(chezmoi diff 2>&1)

    if [[ -z "$diff_output" ]]; then
        log_success "All dotfiles are in sync"
        return 0
    else
        log_warning "Dotfiles have differences:"
        echo "$diff_output"
        return 1
    fi
}

# ============================================================================
# MANAGED FILES
# ============================================================================

# List managed files
list_managed_files() {
    log_header "Managed Dotfiles"

    if ! verify_chezmoi_installed; then
        log_error "chezmoi not installed"
        return 1
    fi

    if ! verify_chezmoi_initialized; then
        log_error "chezmoi not initialized"
        return 1
    fi

    chezmoi managed
}

# ============================================================================
# STATUS
# ============================================================================

# Show chezmoi status
get_chezmoi_status() {
    log_header "Chezmoi Status"

    if verify_chezmoi_installed; then
        log_success "chezmoi installed: $(get_chezmoi_version)"
    else
        log_error "chezmoi not installed"
        return
    fi

    if verify_chezmoi_initialized; then
        local branch
        branch=$(get_chezmoi_branch)
        log_success "chezmoi initialized (branch: $branch)"
        log_info "Source: $CHEZMOI_SOURCE"
    else
        log_warning "chezmoi not initialized"
        return
    fi

    # Count managed files
    local managed_count
    managed_count=$(chezmoi managed 2>/dev/null | wc -l)
    log_info "Managed files: $managed_count"

    # Check for differences
    local diff_count
    diff_count=$(chezmoi diff 2>/dev/null | grep -c "^diff" || echo "0")

    if [[ "$diff_count" == "0" ]]; then
        log_success "All files in sync"
    else
        log_warning "$diff_count files have differences"
    fi
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full dotfiles setup
setup_dotfiles() {
    local branch="${1:-}"
    local repo="${2:-$DOTFILES_REPO}"
    local errors=0

    install_chezmoi || ((errors++))
    init_and_apply_dotfiles "$branch" "$repo" || ((errors++))

    if [[ $errors -gt 0 ]]; then
        log_warning "Dotfiles setup completed with $errors issues"
        return 1
    fi

    log_success "Dotfiles setup complete"
    return 0
}
