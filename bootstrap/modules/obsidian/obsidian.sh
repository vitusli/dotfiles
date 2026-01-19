#!/bin/bash
# ============================================================================
# OBSIDIAN MODULE
# Handles Obsidian vault configuration linking for macOS/Linux
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"

# ============================================================================
# CONFIGURATION
# ============================================================================

OBSIDIAN_DIR="${OBSIDIAN_DIR:-$HOME/Documents/obsidian}"
OBSIDIAN_SHARED_CONFIG="${OBSIDIAN_SHARED_CONFIG:-obsidian_shared}"

# ============================================================================
# VERIFICATION
# ============================================================================

verify_obsidian_dir() {
    [[ -d "$OBSIDIAN_DIR" ]]
}

verify_shared_config() {
    [[ -d "$OBSIDIAN_DIR/$OBSIDIAN_SHARED_CONFIG/.obsidian" ]]
}

get_obsidian_vaults() {
    local vaults=()
    if [[ -d "$OBSIDIAN_DIR" ]]; then
        for v in "$OBSIDIAN_DIR"/*; do
            [[ -d "$v" ]] || continue
            local base="$(basename "$v")"
            [[ "$base" == .* || "$base" == "$OBSIDIAN_SHARED_CONFIG" ]] && continue
            vaults+=("$v")
        done
    fi
    printf '%s\n' "${vaults[@]}"
}

verify_vault_linked() {
    local vault="$1"
    local target_link="$vault/.obsidian"
    local relative_path="../$OBSIDIAN_SHARED_CONFIG/.obsidian"
    [[ -L "$target_link" ]] && [[ "$(readlink "$target_link")" == "$relative_path" ]]
}

# ============================================================================
# LINKING
# ============================================================================

link_vault() {
    local vault="$1"
    local vault_name="$(basename "$vault")"
    local target_link="$vault/.obsidian"
    local relative_path="../$OBSIDIAN_SHARED_CONFIG/.obsidian"

    if verify_vault_linked "$vault"; then
        log_success "Obsidian config already linked for $vault_name"
        return 0
    fi

    if [[ -e "$target_link" ]] && [[ ! -L "$target_link" ]]; then
        local backup_name="$target_link.bak.$(date +%Y%m%d-%H%M%S)"
        mv "$target_link" "$backup_name"
        log_info "Backed up existing .obsidian in $vault_name"
    fi

    [[ -L "$target_link" ]] && rm "$target_link"
    ln -s "$relative_path" "$target_link"

    if verify_vault_linked "$vault"; then
        log_success "Obsidian config linked for $vault_name"
        return 0
    else
        log_error "Failed to link Obsidian config for $vault_name"
        return 1
    fi
}

unlink_vault() {
    local vault="$1"
    local vault_name="$(basename "$vault")"
    local target_link="$vault/.obsidian"

    if [[ ! -L "$target_link" ]]; then
        log_info "$vault_name is not linked"
        return 0
    fi

    rm "$target_link"
    log_success "Unlinked Obsidian config for $vault_name"
    return 0
}

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

link_obsidian() {
    log_header "Linking Obsidian Configuration"

    local shared_path="$OBSIDIAN_DIR/$OBSIDIAN_SHARED_CONFIG/.obsidian"

    if ! verify_obsidian_dir; then
        log_warning "Obsidian directory not found at $OBSIDIAN_DIR"
        return 0
    fi

    if ! verify_shared_config; then
        log_warning "Shared Obsidian config not found at $shared_path"
        return 0
    fi

    local vaults=()
    while IFS= read -r vault; do
        [[ -n "$vault" ]] && vaults+=("$vault")
    done < <(get_obsidian_vaults)

    if [[ ${#vaults[@]} -eq 0 ]]; then
        log_warning "No Obsidian vaults found in $OBSIDIAN_DIR"
        return 0
    fi

    log_info "Detected ${#vaults[@]} Obsidian vault(s)"

    local errors=0
    for vault in "${vaults[@]}"; do
        link_vault "$vault" || ((errors++))
    done

    if [[ $errors -gt 0 ]]; then
        log_warning "Obsidian linking completed with $errors issues"
        return 1
    fi

    log_success "All Obsidian vaults linked"
    return 0
}

unlink_obsidian() {
    log_header "Unlinking Obsidian Configuration"

    local vaults=()
    while IFS= read -r vault; do
        [[ -n "$vault" ]] && vaults+=("$vault")
    done < <(get_obsidian_vaults)

    if [[ ${#vaults[@]} -eq 0 ]]; then
        log_info "No Obsidian vaults found"
        return 0
    fi

    for vault in "${vaults[@]}"; do
        unlink_vault "$vault"
    done

    log_success "All Obsidian vaults unlinked"
    return 0
}

get_obsidian_status() {
    log_header "Obsidian Status"

    if ! verify_obsidian_dir; then
        log_warning "Obsidian directory not found at $OBSIDIAN_DIR"
        return
    fi

    log_info "Obsidian directory: $OBSIDIAN_DIR"

    if verify_shared_config; then
        log_success "Shared config exists"
    else
        log_warning "Shared config not found"
    fi

    local vaults=()
    while IFS= read -r vault; do
        [[ -n "$vault" ]] && vaults+=("$vault")
    done < <(get_obsidian_vaults)

    log_info "Found ${#vaults[@]} vault(s):"

    for vault in "${vaults[@]}"; do
        local vault_name="$(basename "$vault")"
        if verify_vault_linked "$vault"; then
            log_success "  $vault_name (linked)"
        else
            log_warning "  $vault_name (not linked)"
        fi
    done
}

setup_obsidian() {
    link_obsidian
}
