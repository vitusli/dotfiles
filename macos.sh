#!/bin/zsh

# Download manually and run with zsh
# curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macme.sh | zsh

# Error handler - be selective about what to report
# Don't use set -e because interactive commands like xcode-select --install will break
set +e

# Only trap fatal errors, not normal command failures
SCRIPT_ERROR=0
handle_fatal_error() {
    SCRIPT_ERROR=1
    {
        echo ""
        echo "════════════════════════════════════════════════════════════"
        echo "✗ FATAL SCRIPT ERROR"
        echo "════════════════════════════════════════════════════════════"
        echo "Error Time: $(date)"
        echo "════════════════════════════════════════════════════════════"
    } | tee -a "$LOG_FILE"

    echo ""
    echo "✗ Setup script encountered a fatal error!"
    echo "ℹ Check the log file for details: $LOG_FILE"
}

# ERR trap not used because too many non-fatal errors are triggered
# Instead critical functions are checked manually

# ============================================================================
# CONFIGURATION
# ============================================================================
DOTFILES_DIR="$HOME/dotfiles"
LOG_DIR="$DOTFILES_DIR/logs"
LOG_FILE="$LOG_DIR/setup-$(date +%Y%m%d-%H%M%S).log"
CONFIG_URL="https://raw.githubusercontent.com/vitusli/dotfiles/main/config"
CONFIG_DIR="$DOTFILES_DIR/config"

# ============================================================================
# CONFIG LOADING FUNCTIONS
# ============================================================================

# Load raw content from local file or remote URL (fallback)
# Usage: load_raw "cli.txt"
load_raw() {
    local file="$1"
    local local_path="${CONFIG_DIR}/${file}"
    local url="${CONFIG_URL}/${file}"

    if [ -f "$local_path" ]; then
        cat "$local_path"
    else
        curl -fsSL "$url" 2>/dev/null
    fi
}

# Load packages from config file (local preferred, remote fallback)
# Usage: load_packages "cli.txt" "macos"
# Returns packages that either have no tag OR have the specified platform tag
load_packages() {
    local file="$1"
    local platform="$2"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$' | \
        awk -v p="#${platform}" '!/#/ || $0 ~ p' | \
        grep -v "^[^#]*#linux[[:space:]]*$" | \
        grep -v "^[^#]*#windows[[:space:]]*$" | \
        sed 's/ *#.*//'
}

# Load all packages (no platform filtering, just strip comments)
load_all() {
    local file="$1"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$' | \
        sed 's/ *#.*//'
}

# Load config preserving format (for repos, mas, duti)
load_config() {
    local file="$1"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$'
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Initialize logging
init_logging() {
    mkdir -p "$LOG_DIR"

    # Add header to log file
    {
        echo "════════════════════════════════════════════════════════════"
        echo "macOS Setup & Configuration Script Log"
        echo "════════════════════════════════════════════════════════════"
        echo "Start Time: $(date)"
        echo "Log File: $LOG_FILE"
        echo "User: $(whoami)"
        echo "Hostname: $(hostname)"
        echo "macOS Version: $(sw_vers -productVersion)"
        echo "════════════════════════════════════════════════════════════"
        echo ""
    } >> "$LOG_FILE"
}

log_header() {
    local msg="▶ $1"
    echo "\n════════════════════════════════════════════════════════════"
    echo "$msg"
    echo "════════════════════════════════════════════════════════════"

    echo "" >> "$LOG_FILE"
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "$msg" >> "$LOG_FILE"
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
}

log_success() {
    local msg="✓ $1"
    echo "$msg"
    echo "✓ $1" >> "$LOG_FILE"
}

log_info() {
    local msg="ℹ $1"
    echo "$msg"
    echo "ℹ $1" >> "$LOG_FILE"
}

log_warning() {
    local msg="⚠ $1"
    echo "$msg"
    echo "⚠ $1" >> "$LOG_FILE"
}

log_error() {
    local msg="✗ $1"
    echo "$msg"
    echo "✗ $1" >> "$LOG_FILE"
}

# Smart error checker - only reports real errors
check_error() {
    local exit_code=$1
    local description=$2
    local output=$3

    # If exit code is 0, it's fine
    [ $exit_code -eq 0 ] && return 0

    # If exit code is non-zero but output contains expected keywords, it's likely fine
    if echo "$output" | grep -qi "already\|skipped\|up.to.date"; then
        return 0
    fi

    # Only report if it contains error keywords
    if echo "$output" | grep -qi "error\|failed\|fatal\|permission denied\|no such file"; then
        log_error "$description"
        echo "Details: $output" >> "$LOG_FILE"
        SCRIPT_ERROR=1
        return 1
    fi

    # Default: don't report (too noisy otherwise)
    return 0
}

command_exists() {
    command -v "$1" &> /dev/null
}

is_installed() {
    local package=$1
    local type=$2

    if [ "$type" = "formula" ]; then
        brew list "$package" &> /dev/null 2>&1
    elif [ "$type" = "cask" ]; then
        brew list --cask "$package" &> /dev/null 2>&1
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

# Refresh sudo before operations that might need it
refresh_sudo() {
    sudo -v 2>/dev/null || true
}

# ============================================================================
# XCODE & BREW SETUP
# ============================================================================

setup_xcode() {
    log_header "Setting up Xcode Command Line Tools"

    if xcode-select -p &>/dev/null && [ -d "$(xcode-select --print-path)" ] 2>/dev/null; then
        log_success "Xcode Command Line Tools already installed"
    else
        log_info "Installing Xcode Command Line Tools..."
        # Interactive dialog needs background execution
        (xcode-select --install &) 2>/dev/null || true

        # Wait up to 5 minutes for installation
        log_info "Waiting for Xcode installation... (check the popup if it appeared)"
        local timeout=300
        local elapsed=0
        while ! xcode-select -p &>/dev/null && [ $elapsed -lt $timeout ]; do
            sleep 5
            ((elapsed+=5))
        done

        if xcode-select -p &>/dev/null; then
            log_success "Xcode Command Line Tools installed"
        else
            log_warning "Xcode installation may still be in progress. Please wait and run the script again if needed."
        fi
    fi
}

setup_brew() {
    log_header "Setting up Homebrew"

    if command_exists brew; then
        log_success "Homebrew already installed"
    else
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
            log_error "Failed to install Homebrew"
            return 1
        }
        log_success "Homebrew installed"
    fi

    # Ensure brew environment is loaded
    if [ -f /opt/homebrew/bin/brew ]; then
        if ! grep -q 'eval.*brew shellenv' ~/.zprofile 2>/dev/null; then
            log_info "Adding Homebrew to ~/.zprofile"
            (echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> ~/.zprofile
        else
            log_success "Homebrew already in ~/.zprofile"
        fi
        eval "$(/opt/homebrew/bin/brew shellenv)"
        log_success "Homebrew environment configured"
    fi
}

# ============================================================================
# BREW PACKAGES
# ============================================================================

install_formulae() {
    log_header "Installing Homebrew Formulae"

    log_info "Loading CLI packages from config..."
    local formulae=($(load_packages "cli.txt" "macos"))
    # Add macOS-specific tools
    formulae+=(duti mas)

    local to_install=()

    for formula in "${formulae[@]}"; do
        if is_installed "$formula" "formula"; then
            log_success "$formula"
        else
            log_warning "$formula (will be installed)"
            to_install+=("$formula")
        fi
    done

    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "Installing ${#to_install[@]} new formulae..."
        brew install "${to_install[@]}"
        log_success "Formulae installation complete"
    else
        log_info "All formulae already installed"
    fi
}

install_casks() {
    log_header "Installing Homebrew Casks"

    log_info "Loading GUI apps from config..."
    local casks=($(load_packages "gui.txt" "macos"))

    local to_install=()

    for cask in "${casks[@]}"; do
        if is_installed "$cask" "cask"; then
            log_success "$cask"
        else
            log_warning "$cask (will be installed)"
            to_install+=("$cask")
        fi
    done

    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "Installing ${#to_install[@]} new casks..."
        for cask in "${to_install[@]}"; do
            log_info "Installing cask: $cask"
            brew install --cask "$cask" 2>&1 | tee -a "$LOG_FILE" || log_error "Failed to install $cask"
        done
        log_success "Casks installation complete"
    else
        log_info "All casks already installed"
    fi
}

# ============================================================================
# BREW CLEANUP (Uninstall packages not in config)
# ============================================================================

cleanup_brew() {
    log_header "Cleaning up Homebrew (removing unlisted packages)"

    # Refresh sudo to avoid password prompts during uninstall
    refresh_sudo

    # Load desired packages from config
    log_info "Loading desired packages from config..."
    local desired_formulae=($(load_packages "cli.txt" "macos"))
    # Add macOS-specific tools that are always needed
    desired_formulae+=(duti mas)

    local desired_casks=($(load_packages "gui.txt" "macos"))

    # Get top-level formulae only (brew leaves excludes dependencies automatically)
    # This is the key insight: we only care about "leaf" packages that aren't
    # dependencies of other packages. Everything else is a dependency and should stay.
    log_info "Analyzing installed packages..."
    local leaf_formulae=($(brew leaves 2>/dev/null))
    local installed_casks=($(brew list --cask -1 2>/dev/null))

    # Helper function to check if item is in array
    is_in_array() {
        local item="$1"
        shift
        local arr=("$@")
        for element in "${arr[@]}"; do
            [[ "$element" == "$item" ]] && return 0
        done
        return 1
    }

    # Find formulae to remove (leaf packages not in desired list)
    # Only leaf packages can be safely removed - dependencies are handled by brew autoremove
    local formulae_to_remove=()
    for formula in "${leaf_formulae[@]}"; do
        if ! is_in_array "$formula" "${desired_formulae[@]}"; then
            formulae_to_remove+=("$formula")
        fi
    done

    # Find casks to remove (not in desired list)
    local casks_to_remove=()
    for cask in "${installed_casks[@]}"; do
        if ! is_in_array "$cask" "${desired_casks[@]}"; then
            casks_to_remove+=("$cask")
        fi
    done

    # Report findings
    if [ ${#formulae_to_remove[@]} -eq 0 ] && [ ${#casks_to_remove[@]} -eq 0 ]; then
        log_success "No packages to remove - Homebrew is clean"
        return 0
    fi

    # Show what will be removed
    if [ ${#formulae_to_remove[@]} -gt 0 ]; then
        log_warning "Formulae to remove (${#formulae_to_remove[@]}):"
        for formula in "${formulae_to_remove[@]}"; do
            echo "  - $formula"
        done
    fi

    if [ ${#casks_to_remove[@]} -gt 0 ]; then
        log_warning "Casks to remove (${#casks_to_remove[@]}):"
        for cask in "${casks_to_remove[@]}"; do
            echo "  - $cask"
        done
    fi

    # Ask for confirmation
    echo ""
    read -r "?Do you want to remove these packages? (y/n) " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        log_info "Cleanup skipped by user"
        return 0
    fi

    # Remove casks first (they might depend on formulae)
    if [ ${#casks_to_remove[@]} -gt 0 ]; then
        log_info "Removing ${#casks_to_remove[@]} casks..."
        for cask in "${casks_to_remove[@]}"; do
            # Refresh sudo before each cask to prevent password prompts
            sudo -v 2>/dev/null || true
            log_info "Removing cask: $cask"
            brew uninstall --cask "$cask" 2>&1 | tee -a "$LOG_FILE" || true
        done
        log_success "Casks removed"
    fi

    # Remove formulae
    if [ ${#formulae_to_remove[@]} -gt 0 ]; then
        log_info "Removing ${#formulae_to_remove[@]} formulae..."
        for formula in "${formulae_to_remove[@]}"; do
            log_info "Removing formula: $formula"
            brew uninstall "$formula" 2>&1 | tee -a "$LOG_FILE" || true
        done
        log_success "Formulae removed"
    fi

    # Run brew autoremove to clean up any orphaned dependencies
    log_info "Running brew autoremove to clean orphaned dependencies..."
    brew autoremove 2>&1 | tee -a "$LOG_FILE" || true

    # Run brew cleanup
    log_info "Running brew cleanup..."
    brew cleanup 2>&1 | tee -a "$LOG_FILE" || true

    log_success "Homebrew cleanup complete"
}

# ============================================================================
# APP STORE
# ============================================================================

install_mas_apps() {
    log_header "Installing App Store Apps with mas"

    if ! command_exists mas; then
        log_error "mas not found. Install mas first."
        return 1
    fi

    log_info "Loading Mac App Store apps from config..."
    local mas_apps=()
    while IFS= read -r line; do
        mas_apps+=("$line")
    done < <(load_config "macos-mas.txt")

    for app_info in "${mas_apps[@]}"; do
        local app_id="${app_info%%|*}"
        local app_name="${app_info#*|}"

        if mas list 2>/dev/null | grep -q "^$app_id"; then
            log_success "$app_name (already installed)"
        else
            log_info "Installing $app_name..."
            mas install "$app_id"
            log_success "$app_name installed"
        fi
    done
}

# ============================================================================
# GITHUB SETUP
# ============================================================================

setup_github_auth() {
    log_header "Setting up GitHub Authentication"

    if ! command_exists gh; then
        log_error "GitHub CLI not found"
        return 1
    fi

    if gh auth status &> /dev/null; then
        log_success "GitHub CLI already authenticated"
    else
        log_info "Authenticating with GitHub CLI..."
        gh auth login --scopes repo --web
        log_success "GitHub authentication complete"
    fi
}

setup_ssh_key() {
    log_header "Setting up SSH Key"

    local ssh_key="$HOME/.ssh/id_ed25519"

    if [ -f "$ssh_key" ]; then
        log_success "SSH key already exists"
    else
        log_info "Generating SSH key..."
        mkdir -p "$HOME/.ssh"
        ssh-keygen -t ed25519 -C "vituspach@gmail.com" -f "$ssh_key" -N ""
        eval "$(ssh-agent -s)"
        ssh-add --apple-use-keychain "$ssh_key"

        if command_exists gh; then
            log_info "Adding SSH key to GitHub..."
            echo -n "Enter a name for this Mac (e.g. 'MacBook Pro Work'): "
            read key_title
            key_title="${key_title:-MacBook $(date +%Y-%m-%d)}"
            gh ssh-key add "${ssh_key}.pub" --title "$key_title"
        fi

        log_success "SSH key created and configured"
    fi
}

# ============================================================================
# REPOSITORIES
# ============================================================================

clone_repositories() {
    log_header "Cloning GitHub Repositories"

    log_info "Loading repositories from config..."
    local repos=()
    while IFS= read -r line; do
        repos+=("$line")
    done < <(load_config "repos.txt")

    for repo_info in "${repos[@]}"; do
        local repo="${repo_info%%|*}"
        local repo_path="${repo_info#*|}"
        # Expand variables like $HOME and $DOCUMENTS
        repo_path=$(eval echo "$repo_path")
        local repo_name="${repo##*/}"
        local full_path="$repo_path/$repo_name"

        if [ -d "$full_path" ]; then
            log_success "$repo_name (already cloned)"
        else
            log_info "Cloning $repo_name to $repo_path..."
            mkdir -p "$repo_path"
            gh repo clone "$repo" "$full_path"
            log_success "$repo_name cloned"
        fi
    done
}

# ============================================================================
# DOTFILES
# ============================================================================

apply_dotfiles() {
    log_header "Applying Dotfiles with chezmoi"

    if ! command_exists chezmoi; then
        log_error "chezmoi not found"
        return 1
    fi

    # Check if dotfiles are already applied
    if [ -f "$HOME/.zshrc" ] && chezmoi verify &>/dev/null; then
        log_success "Dotfiles already applied"
    else
        log_info "Initializing and applying dotfiles..."
        chezmoi init --branch macos --apply git@github.com:vitusli/dotfiles.git 2>&1 | tee -a "$LOG_FILE"
        log_success "Dotfiles applied successfully"
    fi
}

# ============================================================================
# VS CODE EXTENSIONS
# ============================================================================

install_vscode_extensions() {
    log_header "Installing VS Code Extensions"

    if ! command_exists code; then
        log_warning "VS Code not installed, skipping extensions"
        return 1
    fi

    log_info "Loading VS Code extensions from config..."
    local extensions=($(load_all "vscode.txt"))
    local to_install=()

    for extension in "${extensions[@]}"; do
        if code --list-extensions 2>/dev/null | grep -qi "^$extension$"; then
            log_info "Already installed: $extension"
        else
            to_install+=("$extension")
            log_info "Queued: $extension"
        fi
    done

    if [ ${#to_install[@]} -gt 0 ]; then
        for extension in "${to_install[@]}"; do
            log_info "Installing: $extension"
            code --install-extension "$extension" >> "$LOG_FILE" 2>&1
            log_success "Installed: $extension"
        done
        log_success "VS Code extensions installation complete"
    else
        log_info "All VS Code extensions already installed"
    fi
}

# ============================================================================
# OBSIDIAN CONFIGURATION
# ============================================================================

link_obsidian() {
    log_header "Linking Obsidian Configuration"

    # Shared Obsidian configuration via symlinks.
    # Creates symlink from each vault's .obsidian to the shared config.
    # Automatically applies to ALL vault directories inside
    # $HOME/Documents/obsidian except:
    #   - hidden directories (names starting with . like .git)
    #   - the shared config directory itself (obsidian_shared)

    local obsidian_dir="$HOME/Documents/obsidian"
    local shared_config="obsidian_shared"
    local shared_path="$obsidian_dir/$shared_config/.obsidian"
    local vaults=()

    # Build vault list dynamically
    if [ -d "$obsidian_dir" ]; then
        for v in "$obsidian_dir"/*; do
            [ -d "$v" ] || continue
            local base="$(basename "$v")"
            # Skip hidden dirs and shared config dir
            if [[ "$base" == .* ]] || [[ "$base" == "$shared_config" ]]; then
                continue
            fi
            vaults+=("$v")
        done
    fi

    if [ ${#vaults[@]} -eq 0 ]; then
        log_warning "No Obsidian vaults found in $obsidian_dir (non-hidden)."
        return
    fi

    log_info "Detected ${#vaults[@]} Obsidian vault(s): ${vaults[@]##*/}"

    if [ ! -d "$shared_path" ]; then
        log_warning "Shared Obsidian config not found at $shared_path. Skipping."
        return
    fi

    for vault in "${vaults[@]}"; do
        local target_link="$vault/.obsidian"
        local relative_path="../$shared_config/.obsidian"

        # Check if already correctly symlinked
        if [ -L "$target_link" ] && [ "$(readlink "$target_link")" = "$relative_path" ]; then
            log_success "Obsidian config already linked for $(basename "$vault")"
        else
            # Backup if a real directory/file exists
            if [ -e "$target_link" ] && [ ! -L "$target_link" ]; then
                local backup_path="$target_link.bak.$(date +%Y%m%d-%H%M%S)"
                log_warning "Backing up existing .obsidian in $(basename "$vault") to $backup_path"
                mv "$target_link" "$backup_path"
            fi

            # Remove old symlink if pointing elsewhere
            [ -L "$target_link" ] && rm "$target_link"

            log_info "Linking Obsidian config for $(basename "$vault")..."
            ln -s "$relative_path" "$target_link"
            log_success "Obsidian config linked for $(basename "$vault")"
        fi
    done
}

# ============================================================================
# SET DEFAULT APPLICATIONS
# ============================================================================

setup_default_apps() {
    log_header "Setting up Default Applications with duti"

    if ! command_exists duti; then
        log_error "duti not found. Install duti first."
        return 1
    fi

    log_info "Loading duti config from config..."
    local duti_configs=()
    while IFS= read -r line; do
        duti_configs+=("$line")
    done < <(load_config "macos-duti.txt")

    for config in "${duti_configs[@]}"; do
        # Parse config: bundle_id|uti|role
        local bundle_id="${config%%|*}"
        local rest="${config#*|}"
        local uti="${rest%|*}"
        local role="${rest##*|}"

        log_info "Setting $uti -> $bundle_id ($role)"
        echo -e "${bundle_id}\t${uti}\t${role}" | duti >> "$LOG_FILE" 2>&1
    done

    log_success "Default applications configured"
}

# ============================================================================
# MACOS MARTA CONFIGURATION
# ============================================================================

setup_marta() {
    log_header "Configuring Marta"

    local launcher="/Applications/Marta.app/Contents/Resources/launcher"

    if [ -f "$launcher" ]; then
        if [ -L "/usr/local/bin/marta" ]; then
            log_success "Marta launcher symlink already exists"
        else
            log_info "Creating Marta launcher symlink..."
            sudo ln -sf "$launcher" /usr/local/bin/marta
            log_success "Marta launcher configured"
        fi

        # Default folder handler is now set via duti (see duti/duti config)
        # log_info "Setting Marta as default folder opener..."
        # defaults write -g NSFileViewer -string org.yanex.marta
        # defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerContentType=public.folder;LSHandlerRoleAll=org.yanex.marta;}'
        # log_success "Marta folder integration configured"
    else
        log_warning "Marta.app not found"
    fi
}

# ============================================================================
# MACOS SYSTEM DEFAULTS
# ============================================================================

setup_system_defaults() {
    log_header "Configuring macOS System Defaults"

    log_info "Loading defaults from config..."

    while IFS='|' read -r domain key type value; do
        # Skip empty lines
        [[ -z "$domain" ]] && continue

        # Expand variables like ${HOME}
        value=$(eval echo "$value")

        # Handle special domain prefixes
        local cmd="defaults write"
        local target_domain="$domain"

        if [[ "$domain" == "-g" ]]; then
            target_domain="-g"
        elif [[ "$domain" == -currentHost* ]]; then
            cmd="defaults -currentHost write"
            target_domain="${domain#-currentHost }"
        fi

        # Build and execute command based on type
        case "$type" in
            bool)
                $cmd "$target_domain" "$key" -bool "$value" 2>/dev/null
                ;;
            int)
                $cmd "$target_domain" "$key" -int "$value" 2>/dev/null
                ;;
            float)
                $cmd "$target_domain" "$key" -float "$value" 2>/dev/null
                ;;
            string)
                $cmd "$target_domain" "$key" -string "$value" 2>/dev/null
                ;;
            array)
                $cmd "$target_domain" "$key" -array $value 2>/dev/null
                ;;
            dict-add)
                $cmd "$target_domain" "$key" -dict-add $value 2>/dev/null
                ;;
            *)
                log_warning "Unknown type: $type for $domain|$key"
                ;;
        esac
    done < <(load_config "macos-defaults.txt")

    # These require sudo - keep separate
    log_info "Applying sudo defaults..."
    sudo spctl --master-disable 2>/dev/null || true
    sudo defaults write /var/db/SystemPolicy-prefs.plist enabled -string no 2>/dev/null || true
    sudo nvram StartupMute=%01 2>/dev/null || true

    log_success "All macOS defaults configured"
}

apply_system_changes() {
    log_header "Applying System Changes"

    log_info "Killing Dock to apply changes..."
    killall Dock 2>/dev/null || true
    killall SystemUIServer 2>/dev/null || true

    log_success "System changes applied"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log_header "macOS Setup & Configuration Script (Idempotent)"
    echo "Starting setup... This may take a while."
    echo "This script can be run multiple times safely."
    echo ""
    log_info "Log file: $LOG_FILE"

    # Core setup
    setup_sudo
    setup_xcode
    setup_brew

    # Brew packages
    install_formulae
    install_casks
    cleanup_brew
    install_mas_apps

    # GitHub
    setup_github_auth
    setup_ssh_key
    clone_repositories

    # Dotfiles
    apply_dotfiles
    link_obsidian

    # VS Code
    install_vscode_extensions

    # Default applications
    setup_default_apps

    # macOS configuration
    setup_marta
    setup_system_defaults
    apply_system_changes

    # Final summary
    log_header "Setup Complete!"

    local end_time=$(date)
    echo "✓ All tasks completed successfully!" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "ℹ Replacing Spotlight with Raycast..." | tee -a "$LOG_FILE"
    open "raycast://extensions/raycast/raycast/replace-spotlight-with-raycast"
    log_success "Spotlight replaced with Raycast"
    echo "" | tee -a "$LOG_FILE"
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "End Time: $end_time" >> "$LOG_FILE"
    echo "════════════════════════════════════════════════════════════" >> "$LOG_FILE"

    read -r "?Do you want to log out now? (y/n) " response
    if [[ "$response" =~ ^[yY]$ ]]; then
        log_info "Logging out..."
        echo "User chose to log out at $(date)" >> "$LOG_FILE"
        osascript -e 'tell application "System Events" to log out'
    else
        log_info "Logout skipped. Please log out manually if needed."
        echo "User skipped logout at $(date)" >> "$LOG_FILE"
    fi
}

# Run main function
init_logging
main "$@"

# Final check
if [ $SCRIPT_ERROR -eq 1 ]; then
    exit 1
fi

exit 0
