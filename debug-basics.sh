#!/bin/zsh

# Debug script for testing basic defaults functionality
#
# Run with:
#   zsh <(curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/debug-basics.sh)

echo "════════════════════════════════════════════════════════════"
echo "DEBUG: Basic Defaults Functionality Test"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "=== Test 1: Simple defaults write ==="
defaults write com.apple.dock autohide -bool true 2>&1
echo "Exit code: $?"

echo ""
echo "=== Test 2: Check zsh version ==="
echo "ZSH_VERSION: $ZSH_VERSION"

echo ""
echo "=== Test 3: Test variable in command ==="
cmd="defaults write"
domain="com.apple.dock"
key="test-key-debug"
$cmd "$domain" "$key" -bool true 2>&1
echo "Exit code: $?"

echo ""
echo "=== Test 4: Check if running as admin ==="
echo "User: $(whoami)"
groups | grep -q admin && echo "Has admin: YES" || echo "Has admin: NO"

echo ""
echo "=== Test 5: Test local variable in function ==="
test_func() {
    local cmd="defaults write"
    local target_domain="com.apple.dock"
    $cmd "$target_domain" "test-func-key" -bool true 2>&1
    echo "Exit code inside function: $?"
}
test_func

echo ""
echo "=== Test 6: Read back test values ==="
echo "autohide: $(defaults read com.apple.dock autohide 2>&1)"
echo "test-key-debug: $(defaults read com.apple.dock test-key-debug 2>&1)"
echo "test-func-key: $(defaults read com.apple.dock test-func-key 2>&1)"

echo ""
echo "=== Test 7: Test the exact pattern from macos.sh ==="
domain="com.apple.dock"
key="debug-pattern-test"
type="bool"
value="true"

local cmd="defaults write"
local target_domain="$domain"

case "$type" in
    bool)
        if $cmd "$target_domain" "$key" -bool "$value" 2>/dev/null; then
            echo "Pattern test: SUCCESS"
        else
            echo "Pattern test: FAILED"
            echo "Trying with explicit error output:"
            $cmd "$target_domain" "$key" -bool "$value" 2>&1
        fi
        ;;
esac

echo ""
echo "=== Test 8: Cleanup test keys ==="
defaults delete com.apple.dock test-key-debug 2>/dev/null
defaults delete com.apple.dock test-func-key 2>/dev/null
defaults delete com.apple.dock debug-pattern-test 2>/dev/null
echo "Cleaned up test keys"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "DEBUG COMPLETE"
echo "════════════════════════════════════════════════════════════"
