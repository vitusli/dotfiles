#!/bin/bash
set -euo pipefail

if command -v brew >/dev/null 2>&1; then
  echo "brew already installed"
  exit 0
fi

echo "Installing Homebrew..."
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
