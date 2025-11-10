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
REPOS=(
    "git@github.com:vitusli/obsidian.git|$HOME/Documents"
    "git@github.com:vitusli/codespace.git|$HOME"
    "git@github.com:vitusli/extensions.git|$HOME/Documents/blenderlokal"
    "git@github.com:vitusli/dotfiles.git|$HOME"
)

FORMULAE=(
    git
    gh
    lazygit
    stow
    zsh-autosuggestions
    zsh-autocomplete
    zsh-syntax-highlighting
    fzf
    zellij
    z
    olets/tap/zsh-abbr
    bat
    ffmpeg
    rar
    mas
)

CASKS=(
    aerospace
    arc
    alacritty
    visual-studio-code
    macvim-app
    obsidian
    zotero
    raycast
    keepassxc
    keeweb
    google-drive
    karabiner-elements
    marta
    onedrive
    microsoft-teams
    microsoft-outlook
    slack
    openvpn-connect
    logi-options+
    figma
    darktable
    spotify
    ableton-live-suite
    rhino
    blender
    superwhisper
    homerow
    github
    windows-app
    #adobe-creative-cloud
    #affinity
)

MAS_APPS=(
    "1291898086|toggltrack"
    "1423210932|flow"
    #1609342064|octane-x
)

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
    
    # Keep sudo session alive
    while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &
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
    
    local to_install=()
    
    for formula in "${FORMULAE[@]}"; do
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
    
    local to_install=()
    
    for cask in "${CASKS[@]}"; do
        if is_installed "$cask" "cask"; then
            log_success "$cask"
        else
            log_warning "$cask (will be installed)"
            to_install+=("$cask")
        fi
    done
    
    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "Installing ${#to_install[@]} new casks..."
        brew install --cask "${to_install[@]}"
        log_success "Casks installation complete"
    else
        log_info "All casks already installed"
    fi
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
    
    for app_info in "${MAS_APPS[@]}"; do
        local app_id="${app_info%|*}"
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
            gh ssh-key add "${ssh_key}.pub" --title "MacBook $(date +%Y-%m-%d)"
        fi
        
        log_success "SSH key created and configured"
    fi
}

# ============================================================================
# REPOSITORIES
# ============================================================================

clone_repositories() {
    log_header "Cloning GitHub Repositories"
    
    for repo_info in "${REPOS[@]}"; do
        local repo_url="${repo_info%|*}"
        local repo_path="${repo_info#*|}"
        local repo_name=$(basename "$repo_url" .git)
        local full_path="$repo_path/$repo_name"
        
        if [ -d "$full_path" ]; then
            log_success "$repo_name (already cloned)"
        else
            log_info "Cloning $repo_name to $repo_path..."
            mkdir -p "$repo_path"
            git clone "$repo_url" "$full_path"
            log_success "$repo_name cloned"
        fi
    done
}

# ============================================================================
# DOTFILES
# ============================================================================

stow_dotfiles() {
    log_header "Stowing Dotfiles"
    
    if [ ! -d "$DOTFILES_DIR" ]; then
        log_error "Dotfiles directory not found at $DOTFILES_DIR"
        return 1
    fi
    
    if ! command_exists stow; then
        log_error "stow not found"
        return 1
    fi
    
    cd "$DOTFILES_DIR"
    
    if [ -d stow ]; then
        # Check if already stowed by looking for symlinks
        if [ -L "$HOME/.config" ] 2>/dev/null || [ -L "$HOME/.zshrc" ] 2>/dev/null; then
            log_success "Dotfiles already stowed"
        else
            log_info "Running stow..."
            stow --adopt stow
            log_success "Dotfiles stowed successfully"
        fi
    else
        log_warning "stow directory not found in $DOTFILES_DIR"
    fi
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
        
        log_info "Setting Marta as default folder opener..."
        defaults write -g NSFileViewer -string org.yanex.marta
        defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerContentType=public.folder;LSHandlerRoleAll=org.yanex.marta;}'
        log_success "Marta folder integration configured"
    else
        log_warning "Marta.app not found"
    fi
}

# ============================================================================
# MACOS SYSTEM DEFAULTS
# ============================================================================

setup_system_defaults() {
    log_header "Configuring macOS System Defaults"
    
    # Global System Settings
    # Set fastest key repeat rate (1 = fastest)
    defaults write NSGlobalDomain KeyRepeat -int 1
    # Disable automatic spell correction
    defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false
    
    # Trackpad & Mouse
    # Trackpad speed (0.5-2.5 scale, 0.875 = fast)
    defaults write NSGlobalDomain com.apple.mouse.scaling -float .875
    # Enable three-finger drag on trackpad
    defaults write com.apple.AppleMultitouchTrackpad "TrackpadThreeFingerDrag" -bool "true"
    # Disable separate spaces per display (span all displays)
    defaults write com.apple.spaces spans-displays -bool true
    
    # Animation Settings (Disable All)
    # Disable window opening/closing animations
    defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
    # Disable scroll animations
    defaults write -g NSScrollAnimationEnabled -bool false
    # Speed up window resize animations (0.001 = no delay)
    defaults write -g NSWindowResizeTime -float 0.001
    # Disable Quick Look panel animations
    defaults write -g QLPanelAnimationDuration -float 0
    # Disable document revision window animations
    defaults write -g NSDocumentRevisionsWindowTransformAnimation -bool false
    # Disable full screen toolbar animations
    defaults write -g NSToolbarFullScreenAnimationDuration -float 0
    # Disable browser column animations
    defaults write -g NSBrowserColumnAnimationSpeedMultiplier -float 0
    
    # Dock Settings
    # Enable Dock auto-hide
    defaults write com.apple.dock autohide -bool true
    # Remove auto-hide delay (instant show on mouse over)
    defaults write com.apple.dock autohide-delay -float 0
    # Remove auto-hide animation time
    defaults write com.apple.dock autohide-time-modifier -float 0
    # Disable Mission Control animation
    defaults write com.apple.dock expose-animation-duration -float 0
    # Disable Launchpad show animation
    defaults write com.apple.dock springboard-show-duration -float 0
    # Disable Launchpad hide animation
    defaults write com.apple.dock springboard-hide-duration -float 0
    # Disable Launchpad page animation
    defaults write com.apple.dock springboard-page-duration -float 0
    # Don't automatically rearrange Spaces based on most recent use
    defaults write com.apple.dock mru-spaces -bool false
    # Speed up Mission Control animation (0.1 = fast)
    defaults write com.apple.dock expose-animation-duration -float 0.1
    # Group Mission Control windows by application
    defaults write com.apple.dock "expose-group-by-app" -bool true
    
    # Finder Settings
    # Use column view in Finder (Clmv = column view)
    defaults write com.apple.finder FXPreferredViewStyle Clmv
    # Disable all Finder animations
    defaults write com.apple.finder DisableAllAnimations -bool true
    # Show external hard drives and USB on desktop
    defaults write com.apple.finder ShowExternalHardDrivesOnDesktop -bool true
    # Enable text selection in Quick Look preview
    defaults write com.apple.finder QLEnableTextSelection -bool TRUE
    # Don't warn when changing file extension
    defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
    
    # File Extensions
    # Show all filename extensions in Finder
    defaults write NSGlobalDomain AppleShowAllExtensions -bool true
    # Avoid .DS_Store files on network volumes
    defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
    
    # Security & Gatekeeper
    # Disable Gatekeeper (allow any app installation)
    sudo spctl --master-disable 2>/dev/null || true
    # Disable system policy restrictions
    sudo defaults write /var/db/SystemPolicy-prefs.plist enabled -string no 2>/dev/null || true
    # Disable quarantine attributes for downloaded files
    defaults write com.apple.LaunchServices LSQuarantine -bool false
    
    # Save & Print Dialogs
    # Expand save panel by default
    defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
    # Expand print panel by default
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
    # Expand print panel for all apps
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true
    
    # App-Specific Settings
    # Automatically quit printer app after print jobs complete
    defaults write com.apple.print.PrintingPrefs "Quit When Finished" -bool true
    # Disable system-wide resume (don't reopen windows on login)
    defaults write NSGlobalDomain NSQuitAlwaysKeepsWindows -bool false
    # Save to disk by default instead of iCloud
    defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false
    # Disable Mail send animations
    defaults write com.apple.mail DisableSendAnimations -bool true
    # Disable Mail reply animations
    defaults write com.apple.mail DisableReplyAnimations -bool true
    # Don't prompt to use new hard drives as Time Machine backup
    defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool true
    
    # Text & Keyboard
    # Disable smart quotes (useful for programming)
    defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
    # Disable smart dashes (useful for programming)
    defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false
    # Enable full keyboard access for all UI controls (Tab in dialogs)
    defaults write NSGlobalDomain AppleKeyboardUIMode -int 3
    # Enable press-and-hold for accents menu
    defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool true
    # F1/F2 keys behave as standard function keys (not media control)
    defaults write NSGlobalDomain com.apple.keyboard.fnState -bool true
    # fn key does nothing (opposite of above)
    defaults write com.apple.HIToolbox AppleFnUsageType -int "0"
    
    # Download Manager (Transmission)
    # Don't prompt for confirmation before downloading
    defaults write org.m0k.transmission DownloadAsk -bool false
    # Use incomplete folder for downloads in progress
    defaults write org.m0k.transmission UseIncompleteDownloadFolder -bool true
    # Set incomplete downloads folder location
    defaults write org.m0k.transmission IncompleteDownloadFolder -string "${HOME}/Downloads/Incomplete"
    
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
    install_mas_apps
    
    # GitHub
    setup_github_auth
    setup_ssh_key
    clone_repositories
    
    # Dotfiles
    stow_dotfiles
    
    # macOS configuration
    setup_marta
    setup_system_defaults
    apply_system_changes
    
    # Final summary
    log_header "Setup Complete!"
    
    local end_time=$(date)
    echo "✓ All tasks completed successfully!" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "ℹ Next steps:" | tee -a "$LOG_FILE"
    echo "  1. You now have snippets in Raycast: turn off text replacements in System Preferences" | tee -a "$LOG_FILE"
    echo "  2. Log out to apply all system settings (recommended)" | tee -a "$LOG_FILE"
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
