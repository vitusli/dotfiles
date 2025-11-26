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
# Usage: / [-w] [app]  (e.g., / -w marta, / finder, or just /)
/() {
  local search_dirs=(~/Downloads ~/Documents ~/Desktop ~/dotfiles )
  local home_depth=3
  local app=""  # If empty, we'll ask via fzf
  
  # Parse arguments
  local wb_mode=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -w)
        search_dirs=()
        home_depth=0
        wb_mode=true
        search_dirs+=("$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/Asset-Library")
        search_dirs+=("$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/nvidia_omniverse/projects")
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
    if [[ $wb_mode == true ]]; then
      # For -w: only scan top-level directories (maxdepth 1, directories only)
      find_cmd="find ${search_dirs[@]} -mindepth 1 -maxdepth 1 -type d 2>/dev/null"
    else
      # For regular dirs: full recursive search
      find_cmd="find ${search_dirs[@]} 2>/dev/null"
    fi
  fi
  if [[ $home_depth -gt 0 ]]; then
    [[ -n $find_cmd ]] && find_cmd="$find_cmd; "
    find_cmd="${find_cmd}find ~ -maxdepth $home_depth 2>/dev/null"
  fi
  
  # 1) Pick target file/dir
  local target=$(eval "{ $find_cmd; }" | fzf --prompt=": " \
        --preview='[[ -f {} ]] && bat --color=always --style=numbers {} || ls -la {}' \
        --preview-window=right:60%:wrap)
  
  local fzf_exit=$?
  if [[ $fzf_exit -eq 130 ]] || [[ -z $target ]]; then
    return $fzf_exit
  fi
  
  # Copy target to clipboard
  echo -n "$target" | pbcopy
  
  # 2) Pick app if not provided as arg
  if [[ -z "$app" ]]; then
    local app_choice=$( {
        echo "code";
        echo "finder (reveal)";
        echo "marta (open)";
        find /Applications ~/Applications -name "*.app" -maxdepth 2 2>/dev/null;
      } | fzf --prompt="app: " )

    local app_exit=$?
    if [[ $app_exit -eq 130 ]] || [[ -z "$app_choice" ]]; then
      return $app_exit
    fi

    case "$app_choice" in
      "finder (reveal)")
        app="finder"
        ;;
      "marta (open)")
        app="marta"
        ;;
      *.app)
        app=$(basename "$app_choice" .app)
        ;;
      *)
        app="$app_choice"
        ;;
    esac
  fi
  
  # 3) Open with chosen app
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
      if [[ -n "$app" ]]; then
        if open -a "$app" "$target" 2>/dev/null; then
          echo "Opened with $app and copied to clipboard: $target"
        else
          "$app" "$target"
          echo "Opened with $app (cli) and copied to clipboard: $target"
        fi
      fi
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

# assets - Copy asset from library to project folder
assets() {
  local asset_library="$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/Asset-Library"
  local projects_dir="$HOME/Library/CloudStorage/OneDrive-WandelbotsGmbH/nvidia_omniverse/projects"
  
  # 1) Select file or folder from Asset-Library (recursively, excluding hidden files)
  local asset=$(find "$asset_library" -mindepth 1 ! -path '*/\.*' 2>/dev/null | fzf --prompt="Asset: " \
        --preview='[[ -f {} ]] && bat --color=always --style=numbers {} || ls -la {}' \
        --preview-window=right:60%:wrap)
  
  if [[ -z "$asset" ]]; then
    echo "No asset selected"
    return 1
  fi
  
  # 2) Select project folder
  local project_folder=$(find "$projects_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | fzf --prompt="Project: " \
        --preview='ls -la {}' \
        --preview-window=right:60%:wrap)
  
  if [[ -z "$project_folder" ]]; then
    echo "No project selected"
    return 1
  fi
  
  # 3) Select target folder within project
  local target_folder=$(find "$project_folder" -mindepth 1 -type d 2>/dev/null | fzf --prompt="Target folder: " \
        --preview='ls -la {}' \
        --preview-window=right:60%:wrap)
  
  if [[ -z "$target_folder" ]]; then
    echo "No target folder selected"
    return 1
  fi
  
  # 4) Copy the file or folder
  local item_name=$(basename "$asset")
  
  if [[ -d "$asset" ]]; then
    # Copy directory recursively
    cp -r "$asset" "$target_folder/$item_name"
  else
    # Copy file
    cp "$asset" "$target_folder/$item_name"
  fi
  
  if [[ $? -eq 0 ]]; then
    if [[ -d "$asset" ]]; then
      echo "✓ Copied folder: $item_name"
    else
      echo "✓ Copied file: $item_name"
    fi
    echo "  From: $asset"
    echo "  To:   $target_folder/$item_name"
  else
    echo "✗ Failed to copy"
    return 1
  fi
}
