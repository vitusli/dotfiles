# ============================================================================
# PROMPT & ENVIRONMENT
# ============================================================================

# Minimal prompt without username/hostname
PROMPT='%1~ %% '

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"

# ============================================================================
# EXTERNAL TOOLS
# ============================================================================

# z - directory jumping
source /opt/homebrew/etc/profile.d/z.sh

# fzf - fuzzy finder
source <(fzf --zsh)

# zsh-abbr - abbreviations (must be sourced after compinit)
if type brew &>/dev/null; then
  FPATH="$(brew --prefix)/share/zsh-abbr:${FPATH}"
fi
source /opt/homebrew/share/zsh-abbr/zsh-abbr.zsh

# ============================================================================
# LOAD MODULAR CONFIG
# ============================================================================

# Load all .zsh modules
for config_file in ~/.zsh/*.zsh; do
  source "$config_file"
done
