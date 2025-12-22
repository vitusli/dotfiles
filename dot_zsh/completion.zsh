# ============================================================================
# ZSH PLUGINS & COMPLETION
# ============================================================================

# Load completion system
autoload -Uz compinit
compinit -C  # -C flag skips security check for faster startup

# Load chezmoi completion
if command -v chezmoi &>/dev/null; then
  source <(chezmoi completion zsh)
fi

# Load zsh plugins (apt packages)
# Install: sudo apt install zsh-autosuggestions zsh-syntax-highlighting
[ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ] && \
  source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
[ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ] && \
  source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Configure completion menu
zstyle ':completion:*' menu select
