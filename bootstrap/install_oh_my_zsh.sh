#!/bin/bash
set -euo pipefail

if [[ "${OSTYPE:-}" == darwin* ]]; then
  target="macOS"
elif [[ -n "${WSL_DISTRO_NAME:-}" && "${WSL_DISTRO_NAME}" == "Ubuntu" ]]; then
  target="WSL Ubuntu"
else
  echo "Skipping oh-my-zsh install: only macOS and WSL Ubuntu are supported."
  exit 0
fi

if [[ -d "$HOME/.oh-my-zsh" ]]; then
  echo "oh-my-zsh already installed at $HOME/.oh-my-zsh ($target)."
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install oh-my-zsh."
  exit 1
fi

echo "Installing oh-my-zsh on $target..."
git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$HOME/.oh-my-zsh"
echo "oh-my-zsh installed at $HOME/.oh-my-zsh"
