# kein "vituspacholleck@macbookAIR blabla"
PROMPT='%1~ %% '

# Speed up vim mode - reduce escape key delay
export KEYTIMEOUT=1

# vim bindings
bindkey -v

# Cursor shape settings for Zsh in vi mode
function zle-keymap-select() {
    if [[ $KEYMAP == "vicmd" ]] || [[ $1 = 'block' ]]; then
        print -n "\e[2 q"  # Block cursor for normal mode
    elif [[ $KEYMAP == "main" ]] || [[ $KEYMAP == "viins" ]] || [[ $KEYMAP = '' ]] || [[ $1 = 'beam' ]]; then
        print -n "\e[6 q"  # Line cursor for insert mode
    fi
}

function zle-line-init() {
    print -n "\e[6 q"  # Start with line cursor (insert mode)
}

# Register the functions
zle -N zle-keymap-select
zle -N zle-line-init

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

gatekeeper() {
  local app
  read "app?App: "
  
  # Entferne .app suffix wenn vorhanden
  app="${app%.app}"
  
  local app_path="/Applications/${app}.app"
  
  # Prüfe ob App existiert
  if [[ ! -d "$app_path" ]]; then
    echo "Not found"
    return 1
  fi
  
  # Entferne Quarantine
  if xattr -d com.apple.quarantine "$app_path" 2>/dev/null; then
    echo "Done"
  else
    echo "Failed"
    return 1
  fi
}

# f function for file searching with vim
f() {
  if [[ -z $1 ]]; then
    vim $(fzf --preview="bat --color=always {}")
  else
    echo ":)"
  fi
}

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
