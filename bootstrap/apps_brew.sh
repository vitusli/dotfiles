#!/bin/bash
set -euo pipefail
command -v brew >/dev/null

CONFIG_DIR="$(dirname "$0")/config"

# cli packages (git blacklisted on linux)
PKGS=$(awk '/^#/||!NF{next}/#brew/{print $1}' "$CONFIG_DIR/cli.txt" \
  | { [[ "$(uname -s)" == "Linux" ]] && grep -v '^git$' || cat; })

# gui casks (macOS only)
CASKS=""
if [[ "$(uname -s)" == "Darwin" ]]; then
  CASKS=$(awk '/^#/||!NF{next}/#brew/{print $1}' "$CONFIG_DIR/gui.txt")
fi

[[ -n "$PKGS" ]] && brew install $PKGS || true
[[ -n "$CASKS" ]] && brew install --cask $CASKS || true
