#!/bin/zsh
# ============================================================================
# MACOS BOOTSTRAP SCRIPT (MODULAR)
# ============================================================================
# Modular bootstrap script that uses separate modules for each component.
# Each module handles its own verification instead of trusting exit codes.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macos.sh | zsh
#
# Or with specific modules:
#   ./macos.sh --cli --gui
#   ./macos.sh --defaults --duti
#   ./macos.sh --all
#   ./macos.sh --help
# ============================================================================

set +e  # Don't exit on errors - we handle them manually

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"
MODULES_DIR="${SCRIPT_DIR}/modules"

# Logging
DOTFILES_DIR="$HOME/dotfiles"
LOG_DIR="${DOTFILES_DIR}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/macos-setup-$(date +%Y%m%d-%H%M%S).log"
export LOG_FILE

# Config
CONFIG_URL="https://raw.githubusercontent.com/vitusli/dotfiles/main/config"
CONFIG_DIR="${SCRIPT_DIR}/config"
export CONFIG_URL CONFIG_DIR

# Dotfiles
DOTFILES_REPO="vitusli/dotfiles"
DOTFILES_BRANCH="macos"
export DOTFILES_REPO

# ============================================================================
# LOAD LIBRARIES
# ============================================================================

source "${LIB_DIR}/logging.sh"
source "${LIB_DIR}/config.sh"

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

FLAG_BREW=false
FLAG_CLI=false
FLAG_GUI=false
FLAG_MAS=false
FLAG_CLEANUP=false
FLAG_DEFAULTS=false
FLAG_DUTI=false
FLAG_MARTA=false
FLAG_VSCODE=false
FLAG_GITHUB=false
FLAG_REPOS=false
FLAG_DOTFILES=false
FLAG_OBSIDIAN=false
FLAG_SOFTWAREUPDATE=false
FLAG_STATUS=false
FLAG_ALL=false
SELECTIVE_MODE=false

show_help() {
    cat << 'EOF'
Usage: ./macos.sh [OPTIONS]

If no options are provided, runs the full setup.

Options:
  --brew            Install Homebrew only (no packages)
  --cli             Install CLI tools (Homebrew formulae)
  --gui             Install GUI apps (Homebrew casks)
  --mas             Install Mac App Store apps
  --cleanup         Remove unlisted Homebrew packages
  --defaults        Apply macOS system defaults
  --duti            Set default applications
  --marta           Configure Marta file manager
  --vscode          Install VS Code extensions
  --github          Setup GitHub auth & SSH key
  --repos           Clone GitHub repositories
  --dotfiles        Apply dotfiles with chezmoi
  --obsidian        Link shared Obsidian configuration
  --softwareupdate  Download macOS software updates
  --status          Show current system status
  --all             Run full setup (same as no flags)
  --help            Show this help message

Examples:
  ./macos.sh --cli --gui
  ./macos.sh --defaults --duti
  ./macos.sh --github --dotfiles
  ./macos.sh --status
EOF
    exit 0
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --brew)           FLAG_BREW=true; SELECTIVE_MODE=true ;;
        --cli)            FLAG_CLI=true; SELECTIVE_MODE=true ;;
        --gui)            FLAG_GUI=true; SELECTIVE_MODE=true ;;
        --mas)            FLAG_MAS=true; SELECTIVE_MODE=true ;;
        --cleanup)        FLAG_CLEANUP=true; SELECTIVE_MODE=true ;;
        --defaults)       FLAG_DEFAULTS=true; SELECTIVE_MODE=true ;;
        --duti)           FLAG_DUTI=true; SELECTIVE_MODE=true ;;
        --marta)          FLAG_MARTA=true; SELECTIVE_MODE=true ;;
        --vscode)         FLAG_VSCODE=true; SELECTIVE_MODE=true ;;
        --github)         FLAG_GITHUB=true; SELECTIVE_MODE=true ;;
        --repos)          FLAG_REPOS=true; SELECTIVE_MODE=true ;;
        --dotfiles)       FLAG_DOTFILES=true; SELECTIVE_MODE=true ;;
        --obsidian)       FLAG_OBSIDIAN=true; SELECTIVE_MODE=true ;;
        --softwareupdate) FLAG_SOFTWAREUPDATE=true; SELECTIVE_MODE=true ;;
        --status)         FLAG_STATUS=true; SELECTIVE_MODE=true ;;
        --all)            FLAG_ALL=true ;;
        --help|-h)        show_help ;;
        *)                echo "Unknown option: $arg"; show_help ;;
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
# SUDO MANAGEMENT
# ============================================================================

setup_sudo() {
    log_header "Setting up sudo privileges"

    if sudo -n true 2>/dev/null; then
        log_success "sudo already available"
    else
        echo "This script requires administrator privileges."
        sudo -v
        log_success "sudo verified"
    fi

    # Keep sudo session alive - refresh every 30 seconds
    (while true; do sudo -n true; sleep 30; kill -0 "$$" || exit; done) 2>/dev/null &
    SUDO_KEEPALIVE_PID=$!
}

refresh_sudo() {
    sudo -v 2>/dev/null || true
}

# ============================================================================
# LOAD MARTA MODULE
# ============================================================================

MARTA_MODULE="${MODULES_DIR}/marta/marta.sh"
if [[ -f "$MARTA_MODULE" ]]; then
    source "$MARTA_MODULE"
else
    log_warning "Marta module not found at: $MARTA_MODULE"
    setup_marta() { log_warning "Marta module not loaded"; return 1; }
fi

# ============================================================================
# LOAD OBSIDIAN MODULE
# ============================================================================

OBSIDIAN_MODULE="${MODULES_DIR}/obsidian/obsidian.sh"
if [[ -f "$OBSIDIAN_MODULE" ]]; then
    source "$OBSIDIAN_MODULE"
else
    log_warning "Obsidian module not found at: $OBSIDIAN_MODULE"
    link_obsidian() { log_warning "Obsidian module not loaded"; return 1; }
    setup_obsidian() { log_warning "Obsidian module not loaded"; return 1; }
fi

# ============================================================================
# SOFTWARE UPDATES
# ============================================================================

download_software_updates() {
    log_header "Downloading Software Updates"

    log_info "Checking for software updates..."
    local updates
    updates=$(softwareupdate --list 2>&1)

    if echo "$updates" | grep -q "No new software available"; then
        log_success "No software updates available"
    else
        log_info "Software updates found, downloading..."
        softwareupdate --download --all --verbose 2>&1 | tee -a "$LOG_FILE"
        log_success "Software updates downloaded"
    fi
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================

show_status() {
    log_header "System Status"

    echo ""
    log_info "=== Homebrew ==="
    if command -v brew &>/dev/null; then
        local formula_count cask_count
        formula_count=$(brew list --formula | wc -l | tr -d ' ')
        cask_count=$(brew list --cask | wc -l | tr -d ' ')
        log_success "Homebrew: installed"
        log_info "Formulae: $formula_count, Casks: $cask_count"
    else
        log_warning "Homebrew: not installed"
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
        log_success "chezmoi: installed"
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
    log_info "=== VS Code ==="
    if command -v code &>/dev/null; then
        local ext_count
        ext_count=$(code --list-extensions 2>/dev/null | wc -l | tr -d ' ')
        log_success "VS Code: installed ($ext_count extensions)"
    else
        log_warning "VS Code: not installed"
    fi

    echo ""
    log_info "=== macOS ==="
    log_info "Version: $(sw_vers -productVersion)"
    if spctl --status 2>&1 | grep -q "disabled"; then
        log_info "Gatekeeper: disabled"
    else
        log_success "Gatekeeper: enabled"
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
    echo "  macOS Setup Script (Modular)"
    echo "  For Design/Dev Workflow"
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
        echo "  - Homebrew + CLI tools + GUI apps"
        echo "  - Mac App Store apps"
        echo "  - VS Code extensions"
        echo "  - GitHub CLI authentication"
        echo "  - Dotfiles via chezmoi"
        echo "  - macOS system defaults"
        echo ""
        read -r "?Press Enter to continue or Ctrl+C to abort..."
    fi

    local errors=0

    # Core setup
    setup_sudo

    # ========================================
    # BREW (needed for most other things - installs Xcode CLT automatically)
    # ========================================
    if should_run "BREW" || should_run "CLI" || should_run "GUI" || should_run "MAS" || \
       should_run "CLEANUP" || should_run "DUTI" || should_run "VSCODE" || should_run "GITHUB" || \
       should_run "REPOS" || should_run "DOTFILES"; then
        load_module "${MODULES_DIR}/packages/brew.sh"
        install_brew || ((errors++))
    fi

    # ========================================
    # CLI PACKAGES
    # ========================================
    if should_run "CLI"; then
        load_module "${MODULES_DIR}/packages/brew.sh"
        install_formulae || ((errors++))
    fi

    # ========================================
    # GUI PACKAGES
    # ========================================
    if should_run "GUI"; then
        load_module "${MODULES_DIR}/packages/brew.sh"
        install_casks || ((errors++))
    fi

    # ========================================
    # BREW CLEANUP
    # ========================================
    if should_run "CLEANUP"; then
        load_module "${MODULES_DIR}/packages/brew.sh"
        cleanup_brew || ((errors++))
    fi

    # ========================================
    # MAC APP STORE
    # ========================================
    if should_run "MAS"; then
        load_module "${MODULES_DIR}/packages/mas.sh"
        setup_mas || ((errors++))
    fi

    # ========================================
    # GITHUB
    # ========================================
    if should_run "GITHUB"; then
        load_module "${MODULES_DIR}/github/auth.sh"
        setup_git_config || ((errors++))
        setup_github_auth || ((errors++))
        setup_ssh_key || ((errors++))
        add_ssh_key_to_github "MacBook $(date +%Y-%m-%d)" || ((errors++))
    fi

    # ========================================
    # REPOS
    # ========================================
    if should_run "REPOS"; then
        load_module "${MODULES_DIR}/github/auth.sh"
        # Ensure GitHub is set up
        if [[ "$SELECTIVE_MODE" == "true" && "$FLAG_GITHUB" == "false" ]]; then
            setup_github_auth || true
        fi
        clone_repositories || ((errors++))
    fi

    # ========================================
    # DOTFILES
    # ========================================
    if should_run "DOTFILES"; then
        load_module "${MODULES_DIR}/dotfiles/chezmoi.sh"
        setup_dotfiles "$DOTFILES_BRANCH" "$DOTFILES_REPO" || ((errors++))
    fi

    # ========================================
    # OBSIDIAN
    # ========================================
    if should_run "OBSIDIAN"; then
        link_obsidian || ((errors++))
    fi

    # ========================================
    # VS CODE
    # ========================================
    if should_run "VSCODE"; then
        load_module "${MODULES_DIR}/vscode/extensions.sh"
        install_vscode_extensions || ((errors++))
    fi

    # ========================================
    # DEFAULT APPS (DUTI)
    # ========================================
    if should_run "DUTI"; then
        load_module "${MODULES_DIR}/system/macos-duti.sh"
        setup_duti || ((errors++))
    fi

    # ========================================
    # MARTA
    # ========================================
    if should_run "MARTA"; then
        setup_marta || ((errors++))
    fi

    # ========================================
    # SYSTEM DEFAULTS
    # ========================================
    if should_run "DEFAULTS"; then
        load_module "${MODULES_DIR}/system/macos-defaults.sh"
        setup_system_defaults || ((errors++))
    fi

    # ========================================
    # SOFTWARE UPDATES
    # ========================================
    if should_run "SOFTWAREUPDATE"; then
        download_software_updates || ((errors++))
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
    echo "  1. Some changes require logout/restart to take effect"
    echo ""
    echo "  2. Open Raycast and replace Spotlight:"
    echo "     raycast://extensions/raycast/raycast/replace-spotlight-with-raycast"
    echo ""
    echo "  Log file: $LOG_FILE"
    echo ""

    # Only in full mode, offer to open Raycast and logout
    if [[ "$SELECTIVE_MODE" == "false" ]]; then
        log_info "Opening Raycast Spotlight replacement..."
        open "raycast://extensions/raycast/raycast/replace-spotlight-with-raycast" 2>/dev/null || true

        echo ""
        read -r "response?Do you want to log out now? (y/n) "
        if [[ "$response" =~ ^[yY]$ ]]; then
            log_info "Logging out..."
            osascript -e 'tell application "System Events" to log out'
        fi
    fi
}

# Run main
main "$@"
