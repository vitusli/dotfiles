#!/bin/zsh
# VS Code Extensions Installer
# Run this script to reinstall all extensions after a fresh VS Code installation

echo "Installing VS Code extensions..."

while IFS= read -r extension; do
    if [[ -n "$extension" ]]; then
        echo "Installing: $extension"
        code --install-extension "$extension"
    fi
done < "$(dirname "$0")/extensions.txt"

echo "✓ All extensions installed!"
