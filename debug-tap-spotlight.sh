#!/bin/zsh

# Debug script for tap to click and spotlight shortcut
#
# Run with:
#   zsh <(curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/debug-tap-spotlight.sh)

echo "════════════════════════════════════════════════════════════"
echo "DEBUG: Tap to Click & Spotlight Shortcut"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "=== Tap to Click Settings ==="
echo ""
echo "AppleBluetoothMultitouch.trackpad Clicking:"
defaults read com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking 2>&1
echo ""
echo "AppleMultitouchTrackpad Clicking:"
defaults read com.apple.AppleMultitouchTrackpad Clicking 2>&1
echo ""
echo "tapBehavior (currentHost):"
defaults -currentHost read NSGlobalDomain com.apple.mouse.tapBehavior 2>&1
echo ""
echo "tapBehavior (global):"
defaults read NSGlobalDomain com.apple.mouse.tapBehavior 2>&1

echo ""
echo "=== Three Finger Drag ==="
echo ""
echo "AppleMultitouchTrackpad TrackpadThreeFingerDrag:"
defaults read com.apple.AppleMultitouchTrackpad TrackpadThreeFingerDrag 2>&1
echo ""
echo "AppleBluetoothMultitouch.trackpad TrackpadThreeFingerDrag:"
defaults read com.apple.driver.AppleBluetoothMultitouch.trackpad TrackpadThreeFingerDrag 2>&1

echo ""
echo "=== Spotlight Shortcut (key 64 = Cmd+Space) ==="
echo ""
echo "Looking for key 64 in AppleSymbolicHotKeys:"
defaults read com.apple.symbolichotkeys AppleSymbolicHotKeys 2>/dev/null | grep -A5 "64 ="
echo ""

echo "=== Input Source Shortcut (key 60 = Ctrl+Space) ==="
echo ""
echo "Looking for key 60 in AppleSymbolicHotKeys:"
defaults read com.apple.symbolichotkeys AppleSymbolicHotKeys 2>/dev/null | grep -A5 "60 ="

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Expected values:"
echo "  - Clicking: 1 (enabled)"
echo "  - tapBehavior: 1 (enabled)"
echo "  - TrackpadThreeFingerDrag: 1 (enabled)"
echo "  - Shortcut 64 enabled: 0 (disabled)"
echo "  - Shortcut 60 enabled: 0 (disabled)"
echo "════════════════════════════════════════════════════════════"
