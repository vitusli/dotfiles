#!/bin/zsh

# Debug script for testing macos-defaults loading
#
# Run with:
#   zsh <(curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/debug-defaults.sh)

echo "════════════════════════════════════════════════════════════"
echo "DEBUG: macOS Defaults Loading Test"
echo "════════════════════════════════════════════════════════════"
echo ""

CONFIG_DIR="$HOME/dotfiles/config"
CONFIG_URL="https://raw.githubusercontent.com/vitusli/dotfiles/main/config"

load_raw() {
    local file="$1"
    local local_path="${CONFIG_DIR}/${file}"
    if [ -f "$local_path" ]; then
        echo "✓ USING LOCAL: $local_path" >&2
        cat "$local_path"
    else
        echo "✓ USING REMOTE: ${CONFIG_URL}/${file}" >&2
        curl -fsSL "${CONFIG_URL}/${file}" 2>/dev/null
    fi
}

load_config() {
    load_raw "$1" | grep -v "^#" | grep -v "^$"
}

echo "=== Step 1: Testing config source ==="
echo ""
load_config "macos-defaults.txt" > /dev/null
echo ""

echo "=== Step 2: First 5 entries ==="
load_config "macos-defaults.txt" | head -5
echo ""

echo "=== Step 3: Counting entries ==="
count=$(load_config "macos-defaults.txt" | wc -l | tr -d ' ')
echo "Total entries found: $count"
echo ""

if [ "$count" -eq 0 ]; then
    echo "✗ ERROR: No entries loaded! Config file might be missing or empty."
    exit 1
fi

echo "=== Step 4: Testing defaults write loop ==="
success=0
fail=0

while IFS='|' read -r domain key type value; do
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

    # Build command based on type
    case "$type" in
        bool)
            if $cmd "$target_domain" "$key" -bool "$value" 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        int)
            if $cmd "$target_domain" "$key" -int "$value" 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        float)
            if $cmd "$target_domain" "$key" -float "$value" 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        string)
            if $cmd "$target_domain" "$key" -string "$value" 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        array)
            if $cmd "$target_domain" "$key" -array $value 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        dict-add)
            if $cmd "$target_domain" "$key" -dict-add $value 2>/dev/null; then
                ((success++))
            else
                echo "  ✗ FAILED: $domain | $key | $type | $value"
                ((fail++))
            fi
            ;;
        *)
            echo "  ? UNKNOWN TYPE: $type for $domain | $key"
            ((fail++))
            ;;
    esac
done < <(load_config "macos-defaults.txt")

echo ""
echo "════════════════════════════════════════════════════════════"
echo "RESULTS"
echo "════════════════════════════════════════════════════════════"
echo "✓ Successful: $success"
echo "✗ Failed: $fail"
echo ""

if [ "$success" -gt 0 ]; then
    echo "=== Step 5: Verify some values were actually written ==="
    echo ""
    echo "KeyRepeat (should be 1):"
    defaults read NSGlobalDomain KeyRepeat 2>/dev/null || echo "  NOT SET"
    echo ""
    echo "Dock autohide (should be 1):"
    defaults read com.apple.dock autohide 2>/dev/null || echo "  NOT SET"
    echo ""
    echo "Spotlight shortcut 64 enabled (should be 0 = disabled):"
    defaults read com.apple.symbolichotkeys AppleSymbolicHotKeys 2>/dev/null | grep -A2 '"64"' || defaults read com.apple.symbolichotkeys AppleSymbolicHotKeys 2>/dev/null | grep -A2 "64 =" || echo "  NOT SET"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "NOTE: Some changes require logout/login or restart to apply!"
echo "════════════════════════════════════════════════════════════"
