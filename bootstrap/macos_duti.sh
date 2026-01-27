#!/bin/bash
echo "Setting macOS default apps via duti..."

awk -F'|' '/^[^#]/ && NF==2 {print $1, $2, "all"}' "$(dirname "$0")/config/macos-duti.txt" | xargs -n 3 duti -s

echo "Default apps set successfully."
