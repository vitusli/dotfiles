#!/bin/bash
# ============================================================================
# MACOS SYSTEM DEFAULTS MODULE
# Handles macOS system preferences configuration
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# DEFAULTS VERIFICATION
# ============================================================================

# Read a defaults value
get_defaults_value() {
    local domain="$1"
    local key="$2"
    defaults read "$domain" "$key" 2>/dev/null
}

# Check if a defaults value matches expected
verify_defaults_value() {
    local domain="$1"
    local key="$2"
    local expected="$3"

    local actual
    actual=$(get_defaults_value "$domain" "$key")

    [[ "$actual" == "$expected" ]]
}

# Check if global defaults value matches expected
verify_global_defaults() {
    local key="$1"
    local expected="$2"

    local actual
    actual=$(defaults read -g "$key" 2>/dev/null)

    [[ "$actual" == "$expected" ]]
}

# ============================================================================
# FINDER DEFAULTS
# ============================================================================

setup_finder_defaults() {
    log_info "Configuring Finder defaults..."
    local errors=0

    # Show all filename extensions
    defaults write NSGlobalDomain AppleShowAllExtensions -bool true
    if verify_global_defaults "AppleShowAllExtensions" "1"; then
        log_success "Show all filename extensions"
    else
        log_warning "Failed to set: Show all filename extensions"
        ((errors++))
    fi

    # Show hidden files
    defaults write com.apple.finder AppleShowAllFiles -bool true
    if verify_defaults_value "com.apple.finder" "AppleShowAllFiles" "1"; then
        log_success "Show hidden files"
    else
        log_warning "Failed to set: Show hidden files"
        ((errors++))
    fi

    # Show path bar
    defaults write com.apple.finder ShowPathbar -bool true
    if verify_defaults_value "com.apple.finder" "ShowPathbar" "1"; then
        log_success "Show path bar"
    else
        log_warning "Failed to set: Show path bar"
        ((errors++))
    fi

    # Show status bar
    defaults write com.apple.finder ShowStatusBar -bool true
    if verify_defaults_value "com.apple.finder" "ShowStatusBar" "1"; then
        log_success "Show status bar"
    else
        log_warning "Failed to set: Show status bar"
        ((errors++))
    fi

    # Default to list view
    defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
    if verify_defaults_value "com.apple.finder" "FXPreferredViewStyle" "Nlsv"; then
        log_success "Default to list view"
    else
        log_warning "Failed to set: Default to list view"
        ((errors++))
    fi

    # Search current folder by default
    defaults write com.apple.finder FXDefaultSearchScope -string "SCcf"
    if verify_defaults_value "com.apple.finder" "FXDefaultSearchScope" "SCcf"; then
        log_success "Search current folder by default"
    else
        log_warning "Failed to set: Search current folder"
        ((errors++))
    fi

    # Disable warning when changing file extension
    defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
    if verify_defaults_value "com.apple.finder" "FXEnableExtensionChangeWarning" "0"; then
        log_success "Disable extension change warning"
    else
        log_warning "Failed to set: Disable extension change warning"
        ((errors++))
    fi

    # Disable warning when emptying trash
    defaults write com.apple.finder WarnOnEmptyTrash -bool false
    if verify_defaults_value "com.apple.finder" "WarnOnEmptyTrash" "0"; then
        log_success "Disable empty trash warning"
    else
        log_warning "Failed to set: Disable empty trash warning"
        ((errors++))
    fi

    # Keep folders on top when sorting by name
    defaults write com.apple.finder _FXSortFoldersFirst -bool true
    if verify_defaults_value "com.apple.finder" "_FXSortFoldersFirst" "1"; then
        log_success "Keep folders on top"
    else
        log_warning "Failed to set: Keep folders on top"
        ((errors++))
    fi

    # New Finder windows show home folder
    defaults write com.apple.finder NewWindowTarget -string "PfHm"
    defaults write com.apple.finder NewWindowTargetPath -string "file://${HOME}/"
    log_success "New windows show home folder"

    return $errors
}

# ============================================================================
# DOCK DEFAULTS
# ============================================================================

setup_dock_defaults() {
    log_info "Configuring Dock defaults..."
    local errors=0

    # Auto-hide dock
    defaults write com.apple.dock autohide -bool true
    if verify_defaults_value "com.apple.dock" "autohide" "1"; then
        log_success "Auto-hide dock"
    else
        log_warning "Failed to set: Auto-hide dock"
        ((errors++))
    fi

    # Remove auto-hide delay
    defaults write com.apple.dock autohide-delay -float 0
    log_success "Remove auto-hide delay"

    # Set dock icon size
    defaults write com.apple.dock tilesize -int 48
    if verify_defaults_value "com.apple.dock" "tilesize" "48"; then
        log_success "Set dock icon size to 48"
    else
        log_warning "Failed to set: Dock icon size"
        ((errors++))
    fi

    # Don't show recent applications
    defaults write com.apple.dock show-recents -bool false
    if verify_defaults_value "com.apple.dock" "show-recents" "0"; then
        log_success "Don't show recent applications"
    else
        log_warning "Failed to set: Don't show recent apps"
        ((errors++))
    fi

    # Minimize windows into application icon
    defaults write com.apple.dock minimize-to-application -bool true
    if verify_defaults_value "com.apple.dock" "minimize-to-application" "1"; then
        log_success "Minimize to application icon"
    else
        log_warning "Failed to set: Minimize to application"
        ((errors++))
    fi

    # Enable spring loading for all Dock items
    defaults write com.apple.dock enable-spring-load-actions-on-all-items -bool true
    log_success "Enable spring loading"

    # Show indicator lights for open applications
    defaults write com.apple.dock show-process-indicators -bool true
    if verify_defaults_value "com.apple.dock" "show-process-indicators" "1"; then
        log_success "Show process indicators"
    else
        log_warning "Failed to set: Show process indicators"
        ((errors++))
    fi

    return $errors
}

# ============================================================================
# KEYBOARD & INPUT DEFAULTS
# ============================================================================

setup_keyboard_defaults() {
    log_info "Configuring keyboard defaults..."
    local errors=0

    # Enable full keyboard access for all controls
    defaults write NSGlobalDomain AppleKeyboardUIMode -int 3
    if verify_global_defaults "AppleKeyboardUIMode" "3"; then
        log_success "Full keyboard access"
    else
        log_warning "Failed to set: Full keyboard access"
        ((errors++))
    fi

    # Disable auto-correct
    defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false
    if verify_global_defaults "NSAutomaticSpellingCorrectionEnabled" "0"; then
        log_success "Disable auto-correct"
    else
        log_warning "Failed to set: Disable auto-correct"
        ((errors++))
    fi

    # Disable auto-capitalization
    defaults write NSGlobalDomain NSAutomaticCapitalizationEnabled -bool false
    if verify_global_defaults "NSAutomaticCapitalizationEnabled" "0"; then
        log_success "Disable auto-capitalization"
    else
        log_warning "Failed to set: Disable auto-capitalization"
        ((errors++))
    fi

    # Disable smart quotes
    defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
    if verify_global_defaults "NSAutomaticQuoteSubstitutionEnabled" "0"; then
        log_success "Disable smart quotes"
    else
        log_warning "Failed to set: Disable smart quotes"
        ((errors++))
    fi

    # Disable smart dashes
    defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false
    if verify_global_defaults "NSAutomaticDashSubstitutionEnabled" "0"; then
        log_success "Disable smart dashes"
    else
        log_warning "Failed to set: Disable smart dashes"
        ((errors++))
    fi

    # Disable period substitution
    defaults write NSGlobalDomain NSAutomaticPeriodSubstitutionEnabled -bool false
    if verify_global_defaults "NSAutomaticPeriodSubstitutionEnabled" "0"; then
        log_success "Disable period substitution"
    else
        log_warning "Failed to set: Disable period substitution"
        ((errors++))
    fi

    # Set fast key repeat rate
    defaults write NSGlobalDomain KeyRepeat -int 2
    defaults write NSGlobalDomain InitialKeyRepeat -int 15
    log_success "Set fast key repeat rate"

    return $errors
}

# ============================================================================
# TRACKPAD DEFAULTS
# ============================================================================

setup_trackpad_defaults() {
    log_info "Configuring trackpad defaults..."
    local errors=0

    # Enable tap to click
    defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
    defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true
    defaults -currentHost write NSGlobalDomain com.apple.mouse.tapBehavior -int 1
    defaults write NSGlobalDomain com.apple.mouse.tapBehavior -int 1
    log_success "Enable tap to click"

    # Enable three finger drag
    defaults write com.apple.AppleMultitouchTrackpad TrackpadThreeFingerDrag -bool true
    defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad TrackpadThreeFingerDrag -bool true
    log_success "Enable three finger drag"

    # Set tracking speed
    defaults write NSGlobalDomain com.apple.trackpad.scaling -float 2.5
    log_success "Set tracking speed"

    return $errors
}

# ============================================================================
# SECURITY DEFAULTS
# ============================================================================

setup_security_defaults() {
    log_info "Configuring security defaults..."
    local errors=0

    # Require password immediately after sleep
    defaults write com.apple.screensaver askForPassword -int 1
    defaults write com.apple.screensaver askForPasswordDelay -int 0
    log_success "Require password immediately after sleep"

    # Enable firewall
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on >> "$LOG_FILE" 2>&1
    if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "enabled"; then
        log_success "Firewall enabled"
    else
        log_warning "Failed to enable firewall"
        ((errors++))
    fi

    return $errors
}

# ============================================================================
# MISC DEFAULTS
# ============================================================================

setup_misc_defaults() {
    log_info "Configuring miscellaneous defaults..."
    local errors=0

    # Expand save panel by default
    defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
    defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode2 -bool true
    log_success "Expand save panel by default"

    # Expand print panel by default
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
    defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true
    log_success "Expand print panel by default"

    # Save to disk (not iCloud) by default
    defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false
    if verify_global_defaults "NSDocumentSaveNewDocumentsToCloud" "0"; then
        log_success "Save to disk by default"
    else
        log_warning "Failed to set: Save to disk"
        ((errors++))
    fi

    # Disable the "Are you sure you want to open this application?" dialog
    defaults write com.apple.LaunchServices LSQuarantine -bool false
    log_success "Disable app open confirmation"

    # Disable Resume system-wide
    defaults write com.apple.systempreferences NSQuitAlwaysKeepsWindows -bool false
    log_success "Disable Resume system-wide"

    # Disable automatic termination of inactive apps
    defaults write NSGlobalDomain NSDisableAutomaticTermination -bool true
    log_success "Disable automatic app termination"

    # Set sidebar icon size to medium
    defaults write NSGlobalDomain NSTableViewDefaultSizeMode -int 2
    log_success "Set sidebar icon size to medium"

    # Disable the crash reporter
    defaults write com.apple.CrashReporter DialogType -string "none"
    log_success "Disable crash reporter dialog"

    # Set Help Viewer windows to non-floating mode
    defaults write com.apple.helpviewer DevMode -bool true
    log_success "Set Help Viewer to non-floating"

    # Disable disk image verification
    defaults write com.apple.frameworks.diskimages skip-verify -bool true
    defaults write com.apple.frameworks.diskimages skip-verify-locked -bool true
    defaults write com.apple.frameworks.diskimages skip-verify-remote -bool true
    log_success "Disable disk image verification"

    # Automatically open a new Finder window when a volume is mounted
    defaults write com.apple.frameworks.diskimages auto-open-ro-root -bool true
    defaults write com.apple.frameworks.diskimages auto-open-rw-root -bool true
    defaults write com.apple.finder OpenWindowForNewRemovableDisk -bool true
    log_success "Auto-open window for mounted volumes"

    return $errors
}

# ============================================================================
# SCREENSHOT DEFAULTS
# ============================================================================

setup_screenshot_defaults() {
    log_info "Configuring screenshot defaults..."
    local errors=0

    # Save screenshots to Pictures/Screenshots
    local screenshot_dir="$HOME/Pictures/Screenshots"
    mkdir -p "$screenshot_dir"
    defaults write com.apple.screencapture location -string "$screenshot_dir"
    if [[ -d "$screenshot_dir" ]]; then
        log_success "Screenshots saved to ~/Pictures/Screenshots"
    else
        log_warning "Failed to create screenshot directory"
        ((errors++))
    fi

    # Save screenshots as PNG
    defaults write com.apple.screencapture type -string "png"
    if verify_defaults_value "com.apple.screencapture" "type" "png"; then
        log_success "Screenshots saved as PNG"
    else
        log_warning "Failed to set screenshot format"
        ((errors++))
    fi

    # Disable shadow in screenshots
    defaults write com.apple.screencapture disable-shadow -bool true
    log_success "Disable screenshot shadow"

    return $errors
}

# ============================================================================
# SAFARI DEFAULTS
# ============================================================================

setup_safari_defaults() {
    log_info "Configuring Safari defaults..."
    local errors=0

    # Enable Safari's debug menu
    defaults write com.apple.Safari IncludeInternalDebugMenu -bool true
    log_success "Enable Safari debug menu"

    # Enable the Develop menu and Web Inspector
    defaults write com.apple.Safari IncludeDevelopMenu -bool true
    defaults write com.apple.Safari WebKitDeveloperExtrasEnabledPreferenceKey -bool true
    defaults write com.apple.Safari com.apple.Safari.ContentPageGroupIdentifier.WebKit2DeveloperExtrasEnabled -bool true
    log_success "Enable Safari Develop menu"

    # Add context menu item for showing Web Inspector
    defaults write NSGlobalDomain WebKitDeveloperExtras -bool true
    log_success "Enable Web Inspector in context menu"

    # Show full URL in address bar
    defaults write com.apple.Safari ShowFullURLInSmartSearchField -bool true
    log_success "Show full URL in Safari"

    # Prevent Safari from opening 'safe' files automatically
    defaults write com.apple.Safari AutoOpenSafeDownloads -bool false
    log_success "Disable auto-open safe downloads"

    return $errors
}

# ============================================================================
# ACTIVITY MONITOR DEFAULTS
# ============================================================================

setup_activity_monitor_defaults() {
    log_info "Configuring Activity Monitor defaults..."

    # Show all processes
    defaults write com.apple.ActivityMonitor ShowCategory -int 0
    log_success "Show all processes"

    # Sort by CPU usage
    defaults write com.apple.ActivityMonitor SortColumn -string "CPUUsage"
    defaults write com.apple.ActivityMonitor SortDirection -int 0
    log_success "Sort by CPU usage"

    return 0
}

# ============================================================================
# APPLY SYSTEM CHANGES
# ============================================================================

apply_system_changes() {
    log_info "Applying system changes..."

    # Activate settings
    /System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings -u 2>/dev/null || true
    log_success "Settings activated"

    # Reload preferences daemon
    killall cfprefsd 2>/dev/null || true
    log_success "Preferences daemon reloaded"

    # Kill affected applications
    local apps_to_kill=(
        "Dock"
        "Finder"
        "SystemUIServer"
    )

    for app in "${apps_to_kill[@]}"; do
        killall "$app" 2>/dev/null || true
    done
    log_success "System processes restarted"

    log_warning "Some changes may require a logout/restart to take effect"
}

# ============================================================================
# SUDO DEFAULTS
# ============================================================================

setup_sudo_defaults() {
    log_info "Configuring sudo-required defaults..."

    # Disable Gatekeeper
    sudo spctl --master-disable 2>/dev/null || true
    if sudo spctl --status 2>&1 | grep -q "disabled"; then
        log_success "Gatekeeper disabled"
    else
        log_warning "Could not disable Gatekeeper"
    fi

    # Disable startup sound
    sudo nvram StartupMute=%01 2>/dev/null || true
    log_success "Startup sound muted"

    # Enable locate database
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.locate.plist 2>/dev/null || true
    log_success "Locate database enabled"
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run all defaults configuration
setup_system_defaults() {
    log_header "Configuring macOS System Defaults"

    local total_errors=0
    local result

    setup_finder_defaults
    ((total_errors += $?))

    setup_dock_defaults
    ((total_errors += $?))

    setup_keyboard_defaults
    ((total_errors += $?))

    setup_trackpad_defaults
    ((total_errors += $?))

    setup_security_defaults
    ((total_errors += $?))

    setup_misc_defaults
    ((total_errors += $?))

    setup_screenshot_defaults
    ((total_errors += $?))

    setup_safari_defaults
    ((total_errors += $?))

    setup_activity_monitor_defaults
    ((total_errors += $?))

    setup_sudo_defaults

    apply_system_changes

    if [[ $total_errors -gt 0 ]]; then
        log_warning "Defaults configured with $total_errors warnings"
        return 1
    fi

    log_success "All macOS defaults configured"
    return 0
}

# ============================================================================
# STATUS
# ============================================================================

get_defaults_status() {
    log_header "macOS Defaults Status"

    log_info "=== Finder ==="
    if verify_defaults_value "com.apple.finder" "AppleShowAllFiles" "1"; then
        log_success "Hidden files: shown"
    else
        log_info "Hidden files: hidden"
    fi

    if verify_global_defaults "AppleShowAllExtensions" "1"; then
        log_success "File extensions: shown"
    else
        log_info "File extensions: hidden"
    fi

    log_info "=== Dock ==="
    if verify_defaults_value "com.apple.dock" "autohide" "1"; then
        log_success "Dock auto-hide: enabled"
    else
        log_info "Dock auto-hide: disabled"
    fi

    local dock_size
    dock_size=$(get_defaults_value "com.apple.dock" "tilesize")
    log_info "Dock icon size: $dock_size"

    log_info "=== Security ==="
    if sudo spctl --status 2>&1 | grep -q "disabled"; then
        log_info "Gatekeeper: disabled"
    else
        log_success "Gatekeeper: enabled"
    fi

    if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>&1 | grep -q "enabled"; then
        log_success "Firewall: enabled"
    else
        log_warning "Firewall: disabled"
    fi
}
