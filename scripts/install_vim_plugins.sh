#!/usr/bin/env bash
set -euo pipefail

echo "[vim-plugins] installing fzf + fzf.vim (not vendored)" >&2

# ensure base directory exists
plugdir="$HOME/.vim/pack/plugins/start"
mkdir -p "$plugdir"

# install fzf binary via homebrew if missing
if ! command -v fzf >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "[vim-plugins] installing fzf via homebrew" >&2
    brew install fzf
  else
    echo "[vim-plugins] homebrew not found; please install fzf manually" >&2
  fi
fi

clone_or_update() {
  local repo_url="$1"; shift
  local target="$1"; shift
  if [ -d "$target/.git" ]; then
    echo "[vim-plugins] updating $(basename "$target")" >&2
    git -C "$target" pull --ff-only || {
      echo "[vim-plugins] failed to update $target" >&2
      return 1
    }
  else
    if [ -e "$target" ]; then
      echo "[vim-plugins] target path exists but is not a git repo: $target" >&2
      return 1
    fi
    echo "[vim-plugins] cloning $(basename "$target")" >&2
    git clone --depth 1 "$repo_url" "$target"
  fi
}

clone_or_update https://github.com/junegunn/fzf.git "$plugdir/fzf"
clone_or_update https://github.com/junegunn/fzf.vim.git "$plugdir/fzf.vim"

echo "[vim-plugins] done" >&2