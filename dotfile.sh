#!/bin/zsh

# Passwort am Anfang abfragen und sudo-Zugang für die Dauer des Skripts aufrechterhalten
echo "Dieses Skript benötigt Administrator-Rechte."
sudo -v

# Sudo-Session während der Skript-Ausführung am Leben halten
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

xcode-select --install

echo "Installing Brew..."
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
(echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

echo "Installing Formulae and Casks..."
formulae=(
    git
    gh
    lazygit
    neovim
    stow
    zsh-autosuggestions
    zsh-autocomplete
    zsh-syntax-highlighting
    fzf
    zsh-vi-mode
    zellij
    z
    olets/tap/zsh-abbr
    bat # preview for fzf
    qlmarkdown # quicklook for markdown
    ffmpeg #yt downloader und mp4 aus frames erstellen
)
brew install ${formulae[@]}

casks=(
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
    adobe-creative-cloud
    figma
    miro
    darktable
    spotify
    ableton-live-suite@12
    rhino
    blender
    superwhisper
    homerow
    github
    mas
)
brew install --cask ${casks[@]}

echo "Installing Apps from App Store with mas..."
### App Store
mas install 1291898086 # toggltrack
mas install 1423210932 # flow
# mas install 1609342064 # Octane X

echo "Cloning github repositories..." #is this via ssh? the new machine should register its ssh to github first
### repositories
git clone https://github.com/vitusli/.obsidian.git ~/Documents #repo name changed obsidian
git clone https://github.com/vitusli/codespace.git ~
git clone https://github.com/vitusli/4.5.git ~/Library/Application Support/Blender
git clone https://github.com/hkdobrev/cleanmac.git ~/Documents
git clone https://github.com/vitusli/.dotfiles.git ~ #repo name changed to dotfiles

echo "Stowing dotfiles..."
### stow
cd ~/.dotfiles
stow --adopt stow
exec zsh

echo "Changing macOS defaults..."
# to reactivate commands, type them without the flag
# [Reference](https://macos-defaults.com/keyboard)
### marta 
# command-line launcher
ln -s /Applications/Marta.app/Contents/Resources/launcher /usr/local/bin/marta
# set marta as default app for opening folders
defaults write -g NSFileViewer -string org.yanex.marta
defaults write com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers -array-add '{LSHandlerContentType="public.folder";LSHandlerRoleAll="org.yanex.marta";}'

## Global System Settings
# Set fastest key repeat rate
defaults write NSGlobalDomain KeyRepeat -int 1
# Disable automatic spell correction
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

## Window Management & Gestures
# trackpad speed
defaults write NSGlobalDomain com.apple.mouse.scaling -float .875
#Dragging with three finger drag
defaults write com.apple.AppleMultitouchTrackpad "TrackpadThreeFingerDrag" -bool "true"
# Disable seperate spaces on displays
defaults write com.apple.spaces spans-displays -bool true && killall SystemUIServer

## Animation Settings (Disable All)
# Disable window animations globally
defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
# Disable scroll animations
defaults write -g NSScrollAnimationEnabled -bool false
# Speed up window resize animations
defaults write -g NSWindowResizeTime -float 0.001
# Disable Quick Look panel animations
defaults write -g QLPanelAnimationDuration -float 0
# Disable document revision window animations
defaults write -g NSDocumentRevisionsWindowTransformAnimation -bool false
# Disable toolbar animations in full screen
defaults write -g NSToolbarFullScreenAnimationDuration -float 0
# Disable browser column animations
defaults write -g NSBrowserColumnAnimationSpeedMultiplier -float 0

## Dock Settings
# Enable dock auto-hide
defaults write com.apple.dock autohide -bool true
# Remove dock auto-hide delay
defaults write com.apple.dock autohide-delay -float 0
# Remove dock auto-hide animation time
defaults write com.apple.dock autohide-time-modifier -float 0
# Disable Mission Control animations
defaults write com.apple.dock expose-animation-duration -float 0
# Disable Launchpad animations
defaults write com.apple.dock springboard-show-duration -float 0
defaults write com.apple.dock springboard-hide-duration -float 0
defaults write com.apple.dock springboard-page-duration -float 0

## Finder Settings
# Disable all Finder animations
defaults write com.apple.finder DisableAllAnimations -bool true
# Hide external hard drives on desktop
defaults write com.apple.finder ShowExternalHardDrivesOnDesktop -bool false
# Enable text selection in Quick Look
defaults write com.apple.finder QLEnableTextSelection -bool TRUE

## App-Specific Settings
# Prevent Time Machine from prompting to use new hard drives as backup volume
defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool YES
# Disable Mail send animations
defaults write com.apple.Mail DisableSendAnimations -bool true
# Disable Mail reply animations
defaults write com.apple.Mail DisableReplyAnimations -bool true

#"Disabling OS X Gate Keeper"
#"(You'll be able to install any app you want from here on, not just Mac App Store apps)"
sudo spctl --master-disable
sudo defaults write /var/db/SystemPolicy-prefs.plist enabled -string no
defaults write com.apple.LaunchServices LSQuarantine -bool false

#"Expanding the save panel by default"
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true

#"Automatically quit printer app once the print jobs complete"
defaults write com.apple.print.PrintingPrefs "Quit When Finished" -bool true

#"Saving to disk (not to iCloud) by default"
defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false

#"Disable smart quotes and smart dashes as they are annoying when typing code"
defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false

#"Enabling full keyboard access for all controls (e.g. enable Tab in modal dialogs)"
defaults write NSGlobalDomain AppleKeyboardUIMode -int 3

#"Disabling press-and-hold for keys in favor of a key repeat"
defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool false

#"Showing all filename extensions in Finder by default"
defaults write NSGlobalDomain AppleShowAllExtensions -bool true

#"Use column view in all Finder windows by default"
defaults write com.apple.finder FXPreferredViewStyle Clmv

#"Avoiding the creation of .DS_Store files on network volumes"
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true

#"Setting email addresses to copy as 'foo@example.com' instead of 'Foo Bar <foo@example.com>' in Mail.app"
#defaults write com.apple.mail AddressesIncludeNameOnPasteboard -bool false

#"Don't prompt for confirmation before downloading"
defaults write org.m0k.transmission DownloadAsk -bool false

# Don’t automatically rearrange Spaces based on most recent use
defaults write com.apple.dock mru-spaces -bool false

# F1, F2, etc. behave as standard function keys. Press the fn key to use the special features printed on the key.
defaults write NSGlobalDomain com.apple.keyboard.fnState -bool true

# fn key does nothing
defaults write com.apple.HIToolbox AppleFnUsageType -int "0"

# By default, when a key is held down, the accents menu is displayed.
defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool true

killall Dock

# disable hotkey spotlight
