# ============================================================================
# ZSH PLUGINS & COMPLETION
# ============================================================================

# Case-insensitive globbing and completion (like PowerShell)
unsetopt CASE_GLOB
unsetopt CASE_MATCH
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# Add brew completions to FPATH (macOS + WSL Ubuntu)
if [[ "$OSTYPE" == darwin* ]] || [[ -n "$WSL_DISTRO_NAME" ]]; then
  if command -v brew >/dev/null 2>&1; then
    BREW_PREFIX="$(brew --prefix 2>/dev/null)"
    if [[ -n "$BREW_PREFIX" ]]; then
      FPATH="$BREW_PREFIX/share/zsh/site-functions:${FPATH}"
    fi
  fi
fi

# Load completion system only when omz did not initialize it yet.
if ! typeset -f _main_complete >/dev/null 2>&1; then
  autoload -Uz compinit
  compinit -C
fi

# Load nova completion
if command -v nova &>/dev/null; then
  source <(nova completion zsh)
fi

# Load chezmoi completion
if command -v chezmoi &>/dev/null; then
  source <(chezmoi completion zsh)
fi

# Configure completion menu
zstyle ':completion:*' menu select
