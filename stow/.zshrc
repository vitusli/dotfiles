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

# / function for fuzzy finding directories/files and opening in VS Code or Vim
/() {
  # First, select a directory
  local dir=$(find ~ -type d 2>/dev/null | fzf --prompt="Select directory: " --preview="ls -la {}")
  
  if [[ -z $dir ]]; then
    return 0
  fi
  
  # Then, optionally select a file in that directory
  local file=$(find "$dir" -type f 2>/dev/null | fzf --prompt="Select file (or ESC for directory): " --preview="bat --color=always --style=numbers {}" || echo "")
  
  # Determine what to open
  local target=""
  if [[ -n $file ]]; then
    target="$file"
  else
    target="$dir"
  fi
  
  # Copy to clipboard
  echo -n "$target" | pbcopy
  
  # Ask where to open
  local editor=$(echo -e "code\nvim" | fzf --prompt="Open in code or vim: " --height=3)
  
  if [[ $editor == "vim" ]]; then
    vim "$target"
  elif [[ $editor == "code" ]]; then
    code "$target"
  fi
  
  echo "Copied to clipboard: $target"
}

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
