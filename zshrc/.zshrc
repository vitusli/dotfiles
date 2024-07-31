source /opt/homebrew/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh

eval "$(starship init zsh)"

alias r="ranger"
#alias f="vim $(fzf)" does not work, instead use the following

f() {
  if [[ -z $1 ]]; then
    vim $(fzf)
  else
    vim $1
  fi
}


# zsh fzf
source <(fzf --zsh)

bindkey "^[[1;3D" backward-word # ALT-left-arrow  ⌥ + ←
bindkey "^[[1;3C" forward-word  # ALT-right-arrow ⌥ + →


source $HOMEBREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

source $HOMEBREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh
