#!/bin/bash
set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519"
PUB_KEY="$SSH_KEY.pub"
KNOWN_HOSTS="$HOME/.ssh/known_hosts"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Ensure github.com host key is present once
if ! ssh-keygen -F github.com >/dev/null 2>&1; then
  ssh-keyscan github.com >> "$KNOWN_HOSTS" 2>/dev/null || true
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh is not installed yet. Skipping GitHub auth setup."
  exit 0
fi

if gh auth status >/dev/null 2>&1; then
  echo "gh is already authenticated."
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  echo "Authenticating gh with GITHUB_TOKEN..."
  echo "$GITHUB_TOKEN" | gh auth login --with-token
  echo "gh authenticated successfully."
else
  echo "Authenticating gh via browser (device flow)..."
  gh auth login -p ssh -h github.com
fi

if [[ -f "$PUB_KEY" ]]; then
  KEY_TITLE="$(hostname -s)-$(date +%Y-%m-%d)"
  gh ssh-key add "$PUB_KEY" --title "$KEY_TITLE" >/dev/null 2>&1 || true
  echo "Ensured SSH key is registered in GitHub (if not already present)."
else
  echo "No public key found at $PUB_KEY. Skipping GitHub SSH key upload."
fi
