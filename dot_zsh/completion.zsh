# ============================================================================
# ZSH PLUGINS & COMPLETION
# ============================================================================

# Add Homebrew completions to FPATH
FPATH="/opt/homebrew/share/zsh/site-functions:${FPATH}"

# Load completion system with smart cache invalidation
autoload -Uz compinit
if [[ /opt/homebrew/share/zsh/site-functions -nt ~/.zcompdump ]]; then
  compinit
else
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

# Load zsh plugins
source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Configure completion menu
zstyle ':completion:*' menu select
