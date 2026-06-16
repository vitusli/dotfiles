#!/bin/bash
set -euo pipefail

echo "Setting macOS default apps via duti..."

CONFIG_FILE="$(dirname "$0")/config/macos-duti.txt"

if ! command -v duti >/dev/null 2>&1; then
	if command -v brew >/dev/null 2>&1; then
		echo "duti not found. Installing via Homebrew..."
		brew install duti
	else
		echo "Warning: duti is not installed and Homebrew is unavailable. Skipping default app setup."
		exit 0
	fi
fi

awk -F'|' '/^[^#]/ && NF==2 {print $1, $2, "all"}' "$CONFIG_FILE" | xargs -n 3 duti -s

echo "Default apps set successfully."
