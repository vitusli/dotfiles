#!/bin/bash
set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519"

# 1. SSH-Key generieren falls nicht vorhanden
if [[ ! -f "$SSH_KEY" ]]; then
  echo "Generating SSH key..."
  mkdir -p "$HOME/.ssh"
  ssh-keygen -t ed25519 -C "github" -f "$SSH_KEY" -N ""
  eval "$(ssh-agent -s)" >/dev/null
  ssh-add "$SSH_KEY"
  echo "SSH key generated: $SSH_KEY.pub"
else
  echo "SSH key already exists: $SSH_KEY.pub"
fi

# 2. github.com in known_hosts eintragen
ssh-keyscan github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null || true

# 3. gh authentifizieren
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    echo "gh is already authenticated."
  elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
    echo "Authenticating gh with GITHUB_TOKEN..."
    echo "$GITHUB_TOKEN" | gh auth login --with-token
    echo "gh authenticated successfully."
    KEY_TITLE="$(hostname -s)-$(date +%Y-%m-%d)"
    gh ssh-key add "$SSH_KEY.pub" --title "$KEY_TITLE" 2>/dev/null || true
    echo "SSH key registered as '$KEY_TITLE'."
  else
    echo "Authenticating gh via browser (device flow)..."
    gh auth login -p ssh -h github.com || {
      echo "----------------------------------------"
      echo "  gh auth login did not complete."
      echo "  To finish setup manually:"
      echo "  1. Add this SSH key to GitHub:"
      cat "$SSH_KEY.pub"
      echo "     https://github.com/settings/ssh/new"
      echo "  2. Run: gh auth login"
      echo "----------------------------------------"
    }
  fi
else
  echo "gh is not installed yet."
fi
