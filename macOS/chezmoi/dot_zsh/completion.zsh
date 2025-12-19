# ============================================================================
# ZSH PLUGINS & COMPLETION
# ============================================================================

# Load completion system
if type brew &>/dev/null; then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
  autoload -Uz compinit
  compinit -C  # -C flag skips security check for faster startup
fi

# Load nova completion
if command -v nova &>/dev/null; then
  source <(nova completion zsh)
fi

# Load zsh plugins
source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Configure completion menu
zstyle ':completion:*' menu select
