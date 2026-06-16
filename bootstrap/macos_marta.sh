#!/bin/bash
set -euo pipefail

SOURCE="/Applications/Marta.app/Contents/Resources/launcher"

if [[ ! -x "$SOURCE" ]]; then
	echo "Marta launcher not found at $SOURCE. Skipping symlink setup."
	exit 0
fi

if [[ -d "/usr/local/bin" && -w "/usr/local/bin" ]]; then
	TARGET="/usr/local/bin/marta"
else
	mkdir -p "$HOME/.local/bin"
	TARGET="$HOME/.local/bin/marta"
fi

ln -sf "$SOURCE" "$TARGET"
echo "Linked marta launcher to $TARGET"