#!/bin/bash
set -euo pipefail

NVIM_CONFIG="$HOME/.config/nvim"

if [[ -d "$NVIM_CONFIG" ]]; then
  echo "LazyVim already exists at $NVIM_CONFIG, skipping"
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install LazyVim."
  exit 1
fi

echo "Cloning LazyVim starter..."
git clone https://github.com/LazyVim/starter "$NVIM_CONFIG"
rm -rf "$NVIM_CONFIG/.git"
echo "LazyVim installed at $NVIM_CONFIG"
