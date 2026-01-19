#!/bin/bash
# ============================================================================
# ARCH LINUX BOOTSTRAP SCRIPT (MODULAR)
# ============================================================================
# Modular bootstrap script that uses separate modules for each component.
# Each module handles its own verification instead of trusting exit codes.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/linux.sh | bash
#
# Or with specific modules:
#   ./linux.sh --packages --shell --dotfiles
#   ./linux.sh --all
#   ./linux.sh --help
# ============================================================================

set +e  # Don't exit on errors - we handle them manually

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"
MODULES_ DIR="${SCRIPT_DIR}/modules"

# Logging
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/linux-setup-$(date +%Y%m%d-%H%M%S).log"
export LOG_FILE

# Config
CONFIG_URL="https://raw.githubusercontent.com/vitusli/dotfiles/main/config"
CONFIG_DIR="${SCRIPT_DIR}/config"
export CONFIG_URL CONFIG_DIR

# Dotfiles
DOTFILES_REPO="vitusli/dotfiles"
DOTFILES_BRANCH="linux"
export DOTFILES_REPO

# ============================================================================
# LOAD LIBRARIES
# ============================================================================

source "${LIB_DIR}/logging.sh"
source "${LIB_DIR}/config.sh"

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

FLAG_PACKAGES=false
FLAG_NVIDIA=false
FLAG_AUR=false
FLAG_GITHUB=false
FLAG_SHELL=false
FLAG_DOTFILES=false
FLAG_SERVICES=false
FLAG_SWAY=false
FLAG_ALL=false
FLAG_STATUS=false
SELECTIVE_MODE=false

show_help() {
    cat << 'EOF'
Usage: ./linux.sh [OPTIONS]

If no options are provided, runs the full setup.

Options:
  --packages      Install pacman packages from config
  --nvidia        Install NVIDIA drivers (if GPU detected)
  --aur           Install AUR packages (requires yay)
  --github        Setup GitHub auth and SSH key
  --shell         Setup zsh as default shell
  --dotfiles      Apply dotfiles with chezmoi
  --services      Enable system services (pipewire, etc.)
  --sway          Configure Sway autostart
  --status        Show current system status
  --all           Run full setup (same as no flags)
  --help          Show this help message

Examples:
  ./linux.sh --packages --shell
  ./linux.sh --github --dotfiles
  ./linux.sh --status
EOF
    exit 0
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --packages)   FLAG_PACKAGES=true; SELECTIVE_MODE=true ;;
        --nvidia)     FLAG_NVIDIA=true; SELECTIVE_MODE=true ;;
        --aur)        FLAG_AUR=true; SELECTIVE_MODE=true ;;
        --github)     FLAG_GITHUB=true; SELECTIVE_MODE=true ;;
        --shell)      FLAG_SHELL=true; SELECTIVE_MODE=true ;;
        --dotfiles)   FLAG_DOTFILES=true; SELECTIVE_MODE=true ;;
        --services)   FLAG_SERVICES=true; SELECTIVE_MODE=true ;;
        --sway)       FLAG_SWAY=true; SELECTIVE_MODE=true ;;
        --status)     FLAG_STATUS=true; SELECTIVE_MODE=true ;;
        --all)        FLAG_ALL=true ;;
        --help|-h)    show_help ;;
        *)            echo "Unknown option: $arg"; show_help ;;
    esac
done

# Helper function to check if a section should run
should_run() {
    local flag_name="$1"
    if [[ "$SELECTIVE_MODE" == "false" ]] || [[ "$FLAG_ALL" == "true" ]]; then
        return 0
    fi
    eval "[[ \"\$FLAG_$flag_name\" == \"true\" ]]"
}

# ============================================================================
# MODULE LOADING
# ============================================================================

load_module() {
    local module_path="$1"
    if [[ -f "$module_path" ]]; then
        source "$module_path"
        return 0
    else
        log_error "Module not found: $module_path"
        return 1
    fi
}

# ============================================================================
# SERVICES MODULE (inline - simple enough)
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

            # Verify
            if systemctl is-enabled "$svc" &>/dev/null; then
                log_success "$svc enabled"
            else
                log_error "Failed to enable $svc"
            fi
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

            # Verify
            if systemctl --user is-enabled "$svc" &>/dev/null; then
                log_success "$svc enabled"
            else
                log_warning "Could not enable $svc (may not be installed yet)"
            fi
        fi
    done
}

# ============================================================================
# SWAY AUTOSTART MODULE (inline - simple enough)
# ============================================================================

setup_sway_autostart() {
    log_header "Configuring Sway Autostart"

    local zprofile="$HOME/.zprofile"
    local sway_config='
# Start Sway on TTY1
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
    exec sway
fi'

    # Check if already configured
    if [[ -f "$zprofile" ]] && grep -q "exec sway" "$zprofile"; then
        log_success "Sway autostart already configured"
        return 0
    fi

    log_info "Adding Sway autostart to .zprofile..."
    echo "$sway_config" >> "$zprofile"

    # Verify
    if grep -q "exec sway" "$zprofile"; then
        log_success "Sway autostart configured"
    else
        log_error "Failed to configure Sway autostart"
        return 1
    fi
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================

show_status() {
    log_header "System Status"

    echo ""
    log_info "=== Packages ==="
    if command -v pacman &>/dev/null; then
        local pkg_count
        pkg_count=$(pacman -Q | wc -l)
        log_success "Pacman: $pkg_count packages installed"
    fi

    if command -v yay &>/dev/null; then
        log_success "yay: installed"
    else
        log_warning "yay: not installed"
    fi

    echo ""
    log_info "=== Shell ==="
    if command -v zsh &>/dev/null; then
        log_success "zsh: $(zsh --version | head -1)"
    else
        log_warning "zsh: not installed"
    fi

    local current_shell
    current_shell=$(grep "^$(whoami):" /etc/passwd | cut -d: -f7)
    if [[ "$current_shell" == *"zsh"* ]]; then
        log_success "Default shell: zsh"
    else
        log_warning "Default shell: $current_shell"
    fi

    echo ""
    log_info "=== GitHub ==="
    if command -v gh &>/dev/null; then
        if gh auth status &>/dev/null 2>&1; then
            local gh_user
            gh_user=$(gh api user --jq '.login' 2>/dev/null)
            log_success "GitHub CLI: authenticated as $gh_user"
        else
            log_warning "GitHub CLI: not authenticated"
        fi
    else
        log_warning "GitHub CLI: not installed"
    fi

    if [[ -f "$HOME/.ssh/id_ed25519" ]]; then
        log_success "SSH key: exists"
    else
        log_warning "SSH key: not found"
    fi

    echo ""
    log_info "=== Dotfiles ==="
    if command -v chezmoi &>/dev/null; then
        log_success "chezmoi: $(chezmoi --version | head -1)"
        if [[ -d "$HOME/.local/share/chezmoi/.git" ]]; then
            local branch
            branch=$(git -C "$HOME/.local/share/chezmoi" rev-parse --abbrev-ref HEAD 2>/dev/null)
            log_success "chezmoi initialized: branch $branch"
        else
            log_warning "chezmoi: not initialized"
        fi
    else
        log_warning "chezmoi: not installed"
    fi

    echo ""
    log_info "=== Desktop ==="
    if command -v sway &>/dev/null; then
        log_success "sway: installed"
    else
        log_warning "sway: not installed"
    fi

    if lspci | grep -i nvidia &>/dev/null; then
        log_info "NVIDIA GPU detected"
        if pacman -Qi nvidia &>/dev/null; then
            log_success "NVIDIA drivers: installed"
        else
            log_warning "NVIDIA drivers: not installed"
        fi
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    # Initialize logging
    init_logging

    # Handle status flag specially
    if [[ "$FLAG_STATUS" == "true" ]]; then
        show_status
        exit 0
    fi

    # Show intro
    echo "════════════════════════════════════════════════════════════"
    echo "  Arch Linux Setup Script (Modular)"
    echo "  For Design/Dev Workflow with Sway"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    log_info "Log file: $LOG_FILE"
    echo ""

    if [[ "$SELECTIVE_MODE" == "true" && "$FLAG_ALL" == "false" ]]; then
        log_info "Running in selective mode"
    else
        log_info "Running full setup"
        echo ""
        echo "This script will install:"
        echo "  - System packages (pacman)"
        echo "  - AUR packages (yay)"
        echo "  - NVIDIA drivers (if GPU detected)"
        echo "  - zsh as default shell"
        echo "  - GitHub CLI authentication"
        echo "  - Dotfiles via chezmoi"
        echo "  - Sway desktop configuration"
        echo ""
        read -r -p "Press Enter to continue or Ctrl+C to abort..."
    fi

    local errors=0

    # ========================================
    # PACKAGES
    # ========================================
    if should_run "PACKAGES"; then
        load_module "${MODULES_DIR}/packages/pacman.sh"
        update_system || ((errors++))
        install_pacman_packages || ((errors++))
        install_yay || ((errors++))
    fi

    # ========================================
    # NVIDIA
    # ========================================
    if should_run "NVIDIA"; then
        load_module "${MODULES_DIR}/packages/pacman.sh"
        install_nvidia || ((errors++))
    fi

    # ========================================
    # AUR
    # ========================================
    if should_run "AUR"; then
        load_module "${MODULES_DIR}/packages/pacman.sh"
        install_aur_packages || ((errors++))
    fi

    # ========================================
    # GITHUB
    # ========================================
    if should_run "GITHUB"; then
        load_module "${MODULES_DIR}/github/auth.sh"
        setup_git_config || ((errors++))
        setup_github_auth || ((errors++))
        setup_ssh_key || ((errors++))
        add_ssh_key_to_github "Arch $(hostname) $(date +%Y-%m-%d)" || ((errors++))
    fi

    # ========================================
    # SHELL
    # ========================================
    if should_run "SHELL"; then
        load_module "${MODULES_DIR}/shell/zsh.sh"
        setup_zsh || ((errors++))
    fi

    # ========================================
    # DOTFILES
    # ========================================
    if should_run "DOTFILES"; then
        load_module "${MODULES_DIR}/dotfiles/chezmoi.sh"
        setup_dotfiles "$DOTFILES_BRANCH" "$DOTFILES_REPO" || ((errors++))
    fi

    # ========================================
    # SERVICES
    # ========================================
    if should_run "SERVICES"; then
        enable_services || ((errors++))
    fi

    # ========================================
    # SWAY
    # ========================================
    if should_run "SWAY"; then
        setup_sway_autostart || ((errors++))
    fi

    # ========================================
    # SUMMARY
    # ========================================
    log_header "Setup Complete!"
    echo ""

    if [[ $errors -gt 0 ]]; then
        log_warning "Completed with $errors issues - check log for details"
    else
        log_success "All tasks completed successfully!"
    fi

    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  Next steps:"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "  1. Log out and back in (for shell change to take effect)"
    echo ""
    echo "  2. Reboot if NVIDIA drivers were installed"
    echo "     sudo reboot"
    echo ""
    echo "  3. After reboot, Sway will start automatically on TTY1"
    echo "     Or start manually: sway"
    echo ""
    echo "  Log file: $LOG_FILE"
    echo ""
}

# Run main
main "$@"
