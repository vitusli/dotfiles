# kein "vituspacholleck@macbookAIR blabla"
PROMPT='%1~ %% '

# Speed up vim mode - reduce escape key delay
export KEYTIMEOUT=1

# Load vim bindings immediately (essential for workflow)
source $(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh



# Basic aliases
alias v="nvim"
alias l="lazygit"
alias dot="cd && cd .dotfiles && f"
alias od="cd && cd ./Library/Application\ Support/obsidian && nvim Custom\ Dictionary.txt"
alias ff="fzf | pbcopy"
alias python=/opt/homebrew/bin/python3.11
alias pip=/opt/homebrew/bin/pip3.11

# Lazy z function - loads z when first used
z() {
  # Remove this wrapper function
  unfunction z
  # Load z.sh
  source /opt/homebrew/etc/profile.d/z.sh
  # Now call z with the arguments
  _z "$@"
}

# f function with lazy fzf loading
f() {
  if [[ -z $1 ]]; then
    # Load fzf only when actually needed
    if ! command -v fzf &> /dev/null; then
      source <(fzf --zsh)
    fi
    nvim $(fzf --preview="bat --color=always {}")
  else
    echo ":)"
  fi
}

# Lazy loading wrapper for tab completion
_lazy_load_completions() {
  # Remove this wrapper
  unfunction _lazy_load_completions
  
  # Load completion system
  if type brew &>/dev/null; then
    FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
    autoload -Uz compinit
    compinit -C
    FPATH="$(brew --prefix)/share/zsh-abbr:${FPATH}"
  fi
  
  # Load all the good stuff
  source /opt/homebrew/share/zsh-abbr/zsh-abbr.zsh
  source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  
  zstyle ':completion:*' menu select
  
  # Re-bind Tab to normal completion and trigger it
  bindkey '^I' expand-or-complete
  zle expand-or-complete
}

# Bind Tab to lazy loader initially
zle -N _lazy_load_completions
bindkey '^I' _lazy_load_completions

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
