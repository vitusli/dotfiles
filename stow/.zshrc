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

# / function for fuzzy finding files/directories and opening in VS Code (or other app)
# Usage: / [-wb] [app]  (e.g., / -wb marta, / finder, or just /)
/() {
  local search_dirs=(~/Downloads ~/Documents ~/Desktop ~/dotfiles ~/Projects)
  local home_depth=3
  local app="code"  # Default to VS Code
  
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -wb)
        search_dirs=()
        home_depth=0
        search_dirs+=("$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/Asset-Library")
        search_dirs+=("$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/nvidia_omniverse")
        shift
        ;;
      *)
        app="$1"
        shift
        ;;
    esac
  done
  
  # Build find command
  local find_cmd=""
  if [[ ${#search_dirs[@]} -gt 0 ]]; then
    find_cmd="find ${search_dirs[@]} -type f -o -type d 2>/dev/null"
  fi
  if [[ $home_depth -gt 0 ]]; then
    [[ -n $find_cmd ]] && find_cmd="$find_cmd; "
    find_cmd="${find_cmd}find ~ -maxdepth $home_depth -type f -o -type d 2>/dev/null"
  fi
  
  # Find all files and directories
  local target=$(eval "{ $find_cmd; }" | fzf --prompt=": " \
        --preview='[[ -f {} ]] && bat --color=always --style=numbers {} || ls -la {}' \
        --preview-window=right:60%:wrap) || return 130
  
  # If nothing selected, abort
  if [[ -z $target ]]; then
    return 1
  fi
  
  # Copy to clipboard
  echo -n "$target" | pbcopy
  
  # Open with specified app
  case "$app" in
    marta)
      open -a Marta "$target"
      echo "Opened in Marta and copied to clipboard: $target"
      ;;
    finder)
      open -R "$target"
      echo "Revealed in Finder and copied to clipboard: $target"
      ;;
    *)
      "$app" "$target"
      echo "Opened with $app and copied to clipboard: $target"
      ;;
  esac
}

# Fuzzy-find and open macOS applications
/app() {
  local app_path=$(find /Applications ~/Applications -name "*.app" -maxdepth 2 2>/dev/null | fzf --prompt="Select app: ") || return 130
  
  if [[ -z $app_path ]]; then
    return 1
  fi
  
  # Find the executable inside Contents/MacOS/
  local macos_dir="$app_path/Contents/MacOS"
  if [[ -d $macos_dir ]]; then
    # Find the first executable file in MacOS directory
    local executable=$(find "$macos_dir" -type f -perm +111 -maxdepth 1 | head -n 1)
    
    if [[ -n $executable ]]; then
      echo "Running: $executable"
      "$executable"
    else
      echo "No executable found in $macos_dir"
      return 1
    fi
  else
    echo "MacOS directory not found in app bundle"
    return 1
  fi
}

# Add local bin to PATH
export PATH="$PATH:/Users/vituspacholleck/.local/bin"
