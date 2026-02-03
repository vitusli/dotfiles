#!/bin/bash
echo "Installing VS Code extensions..."
awk '/^[^#]/ && NF' "$(dirname "$0")/config/vscode.txt" | xargs -L 1 code --install-extension
echo "Done."
