# ============================================================================
# ZSH-ABBR
# ============================================================================

if command -v brew >/dev/null 2>&1; then
  BREW_PREFIX="$(brew --prefix 2>/dev/null)"
  if [[ -n "$BREW_PREFIX" ]] && [[ -r "$BREW_PREFIX/share/zsh-abbr/zsh-abbr.zsh" ]]; then
    source "$BREW_PREFIX/share/zsh-abbr/zsh-abbr.zsh"
  fi
fi
