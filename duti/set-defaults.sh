#!/bin/zsh

# Apply duti default applications configuration
# Usage: ./duti/set-defaults.sh
# duti reads from stdin: bundle_id uti role (tab or space separated)

DUTI_CONFIG="$(dirname "$0")/duti"

if [ ! -f "$DUTI_CONFIG" ]; then
    echo "✗ Config file not found: $DUTI_CONFIG"
    exit 1
fi

echo "▶ Applying default applications from $DUTI_CONFIG..."

# Filter out comments and empty lines, convert | to tabs, pipe to duti
grep -v '^\s*#' "$DUTI_CONFIG" | grep -v '^\s*$' | sed 's/|/\t/g' | duti

echo "✓ Done!"
