#!/bin/zsh

set -e  # Exit on any error

# ============================================================================
# CONFIGURATION
# ============================================================================
DOTFILES_DIR="$HOME/dotfiles"
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
    zsh-vi-mode
    zellij
    z
    olets/tap/zsh-abbr
    bat
    ffmpeg
    rar
    mas
)

CASKS=(
    nikitabobko/tap/aerospace
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
    microsoft-remote-desktop
    logi-options+
    figma
    darktable
    spotify
    ableton-live-suite@12
    rhino
    blender
    superwhisper
    homerow
    github
)

MAS_APPS=(
    "1291898086|toggltrack"
    "1423210932|flow"
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_header() {
    echo "\n════════════════════════════════════════════════════════════"
    echo "▶ $1"
    echo "════════════════════════════════════════════════════════════"
}

log_success() {
    echo "✓ $1"
}

log_info() {
    echo "ℹ $1"
}

log_warning() {
    echo "⚠ $1"
}

log_error() {
    echo "✗ $1"
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
    
    if command_exists xcode-select && [ -d "$(xcode-select --print-path)/Platforms/MacOSX.platform" ] 2>/dev/null; then
        log_success "Xcode Command Line Tools already installed"
    else
        log_info "Installing Xcode Command Line Tools..."
        xcode-select --install
        log_success "Xcode Command Line Tools installed"
    fi
}

setup_brew() {
    log_header "Setting up Homebrew"
    
    if command_exists brew; then
        log_success "Homebrew already installed"
    else
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
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
    defaults write NSGlobalDomain KeyRepeat -int 1
    defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false
    
    # Trackpad & Mouse
    defaults write NSGlobalDomain com.apple.mouse.scaling -float .875
    defaults write com.apple.AppleMultitouchTrackpad "TrackpadThreeFingerDrag" -bool "true"
    defaults write com.apple.spaces spans-displays -bool true
    
    # Animation Settings (Disable All)
    defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
    defaults write -g NSScrollAnimationEnabled -bool false
    defaults write -g NSWindowResizeTime -float 0.001
    defaults write -g QLPanelAnimationDuration -float 0
    defaults write -g NSDocumentRevisionsWindowTransformAnimation -bool false
    defaults write -g NSToolbarFullScreenAnimationDuration -float 0
    defaults write -g NSBrowserColumnAnimationSpeedMultiplier -float 0
    
    # Dock Settings
    defaults write com.apple.dock autohide -bool true
    defaults write com.apple.dock autohide-delay -float 0
    defaults write com.apple.dock autohide-time-modifier -float 0
    defaults write com.apple.dock expose-animation-duration -float 0
    defaults write com.apple.dock springboard-show-duration -float 0
    defaults write com.apple.dock springboard-hide-duration -float 0
    defaults write com.apple.dock springboard-page-duration -float 0
    defaults write com.apple.dock mru-spaces -bool false
    defaults write com.apple.dock expose-animation-duration -float 0.1
    defaults write com.apple.dock "expose-group-by-app" -bool true
    
    # Finder Settings
    defaults write com.apple.finder FXPreferredViewStyle Clmv
    defaults write com.apple.finder DisableAllAnimations -bool true
    defaults write com.apple.finder ShowExternalHardDrivesOnDesktop -bool true
    defaults write com.apple.finder QLEnableTextSelection -bool TRUE
    defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
    
    # File Extensions
    defaults write NSGlobalDomain AppleShowAllExtensions -bool true
    defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
    
    # Security & Gatekeeper
    sudo spctl --master-disable 2>/dev/null || true
    sudo defaults write /var/db/SystemPolicy-prefs.plist enabled -string no 2>/dev/null || true
    defaults write com.apple.LaunchServices LSQuarantine -bool false
    
    # Save & Print Dialogs
    defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true
    
    # App-Specific Settings
    defaults write com.apple.print.PrintingPrefs "Quit When Finished" -bool true
    defaults write NSGlobalDomain NSQuitAlwaysKeepsWindows -bool false
    defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false
    defaults write com.apple.mail DisableSendAnimations -bool true
    defaults write com.apple.mail DisableReplyAnimations -bool true
    defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool true
    
    # Text & Keyboard
    defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
    defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false
    defaults write NSGlobalDomain AppleKeyboardUIMode -int 3
    defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool true
    defaults write NSGlobalDomain com.apple.keyboard.fnState -bool true
    defaults write com.apple.HIToolbox AppleFnUsageType -int "0"
    
    # Download Manager
    defaults write org.m0k.transmission DownloadAsk -bool false
    defaults write org.m0k.transmission UseIncompleteDownloadFolder -bool true
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
    echo "
    ✓ All tasks completed successfully!
    
    ℹ Next steps:
    1. Verify all applications are installed
    2. Configure Raycast: turn off text replacements in System Preferences
    3. Disable Spotlight hotkey to avoid conflicts with Raycast
    4. Log out to apply all system settings (recommended)
    "
    
    read -r "?Do you want to log out now? (y/n) " response
    if [[ "$response" =~ ^[yY]$ ]]; then
        log_info "Logging out..."
        osascript -e 'tell application "System Events" to log out'
    else
        log_info "Logout skipped. Please log out manually if needed."
    fi
}

# Run main function
main "$@"
