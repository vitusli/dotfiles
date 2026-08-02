#!/bin/bash
set -euo pipefail

if [[ -z "${WSL_DISTRO_NAME:-}" ]]; then
  echo "Skipping default shell setup: this script is WSL-only."
  exit 0
fi

ZSH_PATH="$(command -v zsh)"

if [[ -z "$ZSH_PATH" ]]; then
  echo "zsh not found in PATH."
  exit 1
fi

if [[ "$SHELL" == "$ZSH_PATH" ]]; then
  echo "Default shell already set to $ZSH_PATH"
  exit 0
fi

grep -qx "$ZSH_PATH" /etc/shells || echo "$ZSH_PATH" | sudo tee -a /etc/shells >/dev/null
chsh -s "$ZSH_PATH"

echo "Default shell set to $ZSH_PATH. Restart your WSL session (wsl --shutdown)."
