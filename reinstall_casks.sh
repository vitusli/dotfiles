#!/bin/zsh

# Reinstall Casks Script
# Prüft alle Casks: Wenn App installiert aber nicht via Homebrew → reinstallieren

#    - bridge
#    - microsoft-teams
#    - raycast
#    - zotero

set -e

CASKS=(
    ableton-live-suite
    adobe-creative-cloud
    aerospace
    affinity
    alt-tab
    arc
    basictex
    blender
    bridge
    chatgpt
    darktable
    figma
    ghostty@tip
    github
    google-drive
    homerow
    karabiner-elements
    keepassxc
    keeweb
    logi-options+
    macvim
    marta
    microsoft-outlook
    microsoft-teams
    obsidian
    onedrive
    openvpn-connect
    raycast
    rhino-app
    sf-symbols
    slack
    spotify
    superwhisper
    visual-studio-code
    windows-app
    zotero
)

# Mapping: cask name -> App name (falls unterschiedlich)
declare -A APP_NAMES=(
    [ableton-live-suite]="Ableton Live 12 Suite"
    [adobe-creative-cloud]="Adobe Creative Cloud"
    [aerospace]="AeroSpace"
    [affinity]="Affinity"
    [alt-tab]="AltTab"
    [arc]="Arc"
    [basictex]="BasicTeX"
    [blender]="Blender"
    [bridge]="Bridge"
    [chatgpt]="ChatGPT"
    [darktable]="darktable"
    [figma]="Figma"
    [ghostty@tip]="Ghostty"
    [github]="GitHub Desktop"
    [google-drive]="Google Drive"
    [homerow]="Homerow"
    [karabiner-elements]="Karabiner-Elements"
    [keepassxc]="KeePassXC"
    [keeweb]="KeeWeb"
    [logi-options+]="Logi Options+"
    [macvim]="MacVim"
    [marta]="Marta"
    [microsoft-outlook]="Microsoft Outlook"
    [microsoft-teams]="Microsoft Teams"
    [obsidian]="Obsidian"
    [onedrive]="OneDrive"
    [openvpn-connect]="OpenVPN Connect"
    [raycast]="Raycast"
    [rhino-app]="Rhino"
    [sf-symbols]="SF Symbols"
    [slack]="Slack"
    [spotify]="Spotify"
    [superwhisper]="SuperWhisper"
    [visual-studio-code]="Visual Studio Code"
    [windows-app]="Windows App"
    [zotero]="Zotero"
)

echo "════════════════════════════════════════════════════════════"
echo "▶ Cask Reinstallation Check"
echo "════════════════════════════════════════════════════════════"
echo ""

to_reinstall=()

for cask in "${CASKS[@]}"; do
    # Hole App-Name (oder nutze cask name)
    app_name="${APP_NAMES[$cask]:-$cask}"
    
    # Prüfe ob via Homebrew installiert
    # Entferne @version für die Prüfung (z.B. ghostty@tip -> ghostty)
    cask_base="${cask%%@*}"
    
    if brew list --cask "$cask" &>/dev/null 2>&1 || brew list --cask "$cask_base" &>/dev/null 2>&1; then
        echo "✓ $cask (bereits via Homebrew)"
        continue
    fi
    
    # Prüfe ob App auf dem System installiert ist
    app_installed=false
    
    # Suche in /Applications
    if [ -d "/Applications/${app_name}.app" ]; then
        app_installed=true
    # Suche mit mdfind (Spotlight)
    elif mdfind "kMDItemKind == 'Application'" 2>/dev/null | grep -qi "/${app_name}.app$"; then
        app_installed=true
    # Suche in ~/Applications
    elif [ -d "$HOME/Applications/${app_name}.app" ]; then
        app_installed=true
    fi
    
    if $app_installed; then
        echo "⚠ $cask → App installiert, aber NICHT via Homebrew"
        to_reinstall+=("$cask")
    else
        echo "○ $cask → nicht installiert, übersprungen"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"

if [ ${#to_reinstall[@]} -eq 0 ]; then
    echo "✓ Keine Reinstallation nötig!"
    exit 0
fi

echo "⚠ Folgende Casks werden reinstalliert (${#to_reinstall[@]}):"
for cask in "${to_reinstall[@]}"; do
    echo "   - $cask"
done
echo ""

read -r "?Fortfahren? (y/n) " response
if [[ ! "$response" =~ ^[yY]$ ]]; then
    echo "Abgebrochen."
    exit 0
fi

echo ""
echo "▶ Starte Reinstallation..."
echo ""

for cask in "${to_reinstall[@]}"; do
    app_name="${APP_NAMES[$cask]:-$cask}"
    
    echo "────────────────────────────────────────"
    echo "Reinstalliere: $cask"
    echo "────────────────────────────────────────"
    
    # Schließe App falls offen
    osascript -e "tell application \"$app_name\" to quit" 2>/dev/null || true
    sleep 1
    
    # Lösche existierende App
    if [ -d "/Applications/${app_name}.app" ]; then
        echo "Entferne /Applications/${app_name}.app..."
        sudo rm -rf "/Applications/${app_name}.app"
    fi
    if [ -d "$HOME/Applications/${app_name}.app" ]; then
        echo "Entferne ~/Applications/${app_name}.app..."
        rm -rf "$HOME/Applications/${app_name}.app"
    fi
    
    # Installiere via Homebrew
    echo "Installiere via Homebrew..."
    brew install --cask "$cask"
    
    echo "✓ $cask reinstalliert"
    echo ""
done

echo "════════════════════════════════════════════════════════════"
echo "✓ Reinstallation abgeschlossen!"
echo "════════════════════════════════════════════════════════════"
