#!/bin/bash
set -euo pipefail

if command -v brew >/dev/null 2>&1; then
  echo "brew already installed"
elif [[ -x /opt/homebrew/bin/brew ]]; then
  echo "brew installed but not in PATH"
elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  echo "brew installed but not in PATH"
else
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Make brew available immediately for subsequent bootstrap scripts.
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi
