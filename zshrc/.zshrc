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
# alias b="brew install"
# alias v="nvim"
# alias r="ranger"
# alias l="lazygit"
# alias zz="zellij"
# alias za="zellij a gitup"
# alias zd="zellij a edit_dotfiles"
# alias dot="cd && cd .dotfiles && f"
# alias wm="yabai --start-service && skhd --start-service"
# alias wmend="yabai --stop-service && skhd --stop-service"
# alias wmre="yabai --restart-service && skhd --restart-service"
# alias wmc="yabai --start-service && skhd --start-service && yabai --stop-service && skhd --stop-service && brew services restart sketchybar"

# f alias
f() {
  if [[ -z $1 ]]; then
    nvim $(fzf --preview="bat --color=always {}")
  else
    echo ":)"
  fi
}

# zsh-abbr completions
if type brew &>/dev/null; then
  FPATH=$(brew --prefix)/share/zsh-abbr:$FPATH

  autoload -Uz compinit
    compinit
fi

#z
zstyle ':completion:*' menu select

bindkey "^[[1;3D" backward-word # ALT-left-arrow  ⌥ + ←
bindkey "^[[1;3C" forward-word  # ALT-right-arrow ⌥ + →

# zsh fzf
source <(fzf --zsh)

source /opt/homebrew/etc/profile.d/z.sh

source /opt/homebrew/share/zsh-abbr/zsh-abbr.zsh

source /opt/homebrew//share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

source /opt/homebrew//share/zsh-autosuggestions/zsh-autosuggestions.zsh
