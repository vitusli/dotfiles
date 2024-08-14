source /opt/homebrew/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh

# vim bindings
# bindkey -v
# but better use the zsh-vi-mode plugin
source $(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh

eval "$(starship init zsh)"

if type brew &>/dev/null
then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"

  autoload -Uz compinit
  compinit
fi

#alias
alias b="brew install"
alias v="nvim"
alias r="ranger"
alias l="lazygit"
alias z="zellij"
alias za="zellij a gitup"

f() {
  if [[ -z $1 ]]; then
    nvim $(fzf)
  else
    nvim $1
  fi
}


# zsh fzf
source <(fzf --zsh)

bindkey "^[[1;3D" backward-word # ALT-left-arrow  ⌥ + ←
bindkey "^[[1;3C" forward-word  # ALT-right-arrow ⌥ + →


source $HOMEBREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

source $HOMEBREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh
