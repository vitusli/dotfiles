# kein "vituspacholleck@macbookAIR blabla"
PROMPT='%1~ %% '

# Speed up vim mode - reduce escape key delay
export KEYTIMEOUT=1

# Load vim bindings immediately (essential for workflow)
source $(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh

# Load z for directory jumping
source /opt/homebrew/etc/profile.d/z.sh

# Load fzf
source <(fzf --zsh)

# Load completion system (required for zsh-abbr and general tab completions)
if type brew &>/dev/null; then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
  autoload -Uz compinit
  compinit -C  # -C flag skips security check for faster startup
  FPATH="$(brew --prefix)/share/zsh-abbr:${FPATH}"
fi

# Load zsh plugins
source /opt/homebrew/share/zsh-abbr/zsh-abbr.zsh
source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Configure completion menu
zstyle ':completion:*' menu select

# Basic aliases
alias v="nvim"
alias l="lazygit"
alias dot="cd && cd .dotfiles && f" #needs the f function underneath
alias python=/opt/homebrew/bin/python3.11
alias pip=/opt/homebrew/bin/pip3.11

# f function for file searching with nvim
f() {
  if [[ -z $1 ]]; then
    nvim $(fzf --preview="bat --color=always {}")
  else
    echo ":)"
  fi
}

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
