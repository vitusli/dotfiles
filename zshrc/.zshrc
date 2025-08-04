# Load only if brew is available
if type brew &>/dev/null; then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
  autoload -Uz compinit
  compinit
  FPATH="$(brew --prefix)/share/zsh-abbr:${FPATH}"
  autoload -Uz compinit
  compinit
fi

# vim bindings
source $(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh

# Starship prompt
eval "$(starship init zsh)"

# Aliases
alias v="nvim"
alias l="lazygit"
alias dot="cd && cd .dotfiles && f"
alias od="cd && cd ./Library/Application\ Support/obsidian && nvim Custom\ Dictionary.txt"
alias ff="fzf | pbcopy"
alias python=/opt/homebrew/bin/python3.11
alias pip=/opt/homebrew/bin/pip3.11

# f alias
f() {
  if [[ -z $1 ]]; then
    nvim $(fzf --preview="bat --color=always {}")
  else
    echo ":)"
  fi
}

#z
zstyle ':completion:*' menu select
source /opt/homebrew/etc/profile.d/z.sh

# zsh fzf
source <(fzf --zsh)

# Load zsh-abbr and syntax highlighting
source /opt/homebrew/share/zsh-abbr/zsh-abbr.zsh
source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh

# Start zellij if not already running
if [[ $- == *i* ]] && ! pgrep -x "zellij" > /dev/null; then
    zellij
fi

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
