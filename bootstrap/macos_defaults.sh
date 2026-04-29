#!/bin/bash
echo "Applying macOS defaults..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config/macos-defaults.txt"

echo "macOS defaults applied successfully. Some changes may require a logout/restart."
