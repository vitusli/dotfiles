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

# / function for fuzzy finding directories/files and opening in VS Code
/() {
  # First, select a directory - search specific common directories to avoid hanging
  local dir=$({ find ~/Downloads ~/Documents ~/Desktop ~/dotfiles ~/Projects -type d 2>/dev/null; find ~ -maxdepth 1 -type d 2>/dev/null; } | fzf --prompt="Select directory: " --preview="ls -la {}")
  
  # If no directory selected, abort
  if [[ -z $dir ]]; then
    return 0
  fi
  
  # Then, optionally select a file in that directory
  local file=$(find "$dir" -type f 2>/dev/null | fzf --prompt="Select file (or ESC for directory): " --preview="bat --color=always --style=numbers {}")
  local fzf_exit=$?
  
  # If file selection was cancelled, abort
  if [[ $fzf_exit -ne 0 ]]; then
    return 0
  fi
  
  # Determine what to open
  local target="${file:-$dir}"
  
  # Copy to clipboard and open in VS Code
  echo -n "$target" | pbcopy
  code "$target"
  
  echo "Opened in VS Code and copied to clipboard: $target"
}

# Fuzzy-find and open macOS applications
/app() {
  local app_path=$(find /Applications ~/Applications -name "*.app" -maxdepth 2 2>/dev/null | fzf --prompt="Select app: ")
  
  if [[ -n $app_path ]]; then
    local executable="$app_path/Contents/MacOS/$(basename "$app_path" .app)"
    
    if [[ -x $executable ]]; then
      echo "Running: $executable"
      "$executable"
    else
      echo "Executable not found, trying 'open' instead..."
      open "$app_path"
    fi
  fi
}

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
