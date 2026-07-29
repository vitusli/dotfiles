#!/bin/bash
set -euo pipefail

echo "Setting up SSH key..."

KEY_PATH="$HOME/.ssh/id_ed25519"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [[ ! -f "$KEY_PATH" ]]; then
  ssh-keygen -t ed25519 -C "chezmoi-generated" -f "$KEY_PATH" -N ""
else
  echo "SSH key already exists. Skipping generation."
fi

eval "$(ssh-agent -s)" >/dev/null
ssh-add "$KEY_PATH" >/dev/null 2>&1 || true

echo "SSH setup complete."
