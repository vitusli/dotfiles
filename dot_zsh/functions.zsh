# ============================================================================
# CUSTOM FUNCTIONS
# ============================================================================

# / - Fuzzy find files/directories and open in VS Code
# Usage: /
/() {
  local search_dirs=(~/Downloads ~/Documents ~/Desktop ~/.local/share/chezmoi ~/codespace)
  local home_depth=3
  
  # Build find command
  local find_cmd="find ${search_dirs[@]} 2>/dev/null"
  if [[ $home_depth -gt 0 ]]; then
    find_cmd="$find_cmd; find ~ -maxdepth $home_depth 2>/dev/null"
  fi
  
  # Pick target file/dir
  local target=$(eval "{ $find_cmd; }" | fzf --prompt=": " \
        --preview='[[ -f {} ]] && bat --color=always --style=numbers {} || ls -la {}' \
        --preview-window=right:60%:wrap)
  
  local fzf_exit=$?
  if [[ $fzf_exit -eq 130 ]] || [[ -z $target ]]; then
    return $fzf_exit
  fi
  
  # Copy target to clipboard and open in VS Code
  echo -n "$target" | pbcopy
  code "$target"
  echo "Opened in VS Code: $target"
}

# /app - Fuzzy-find and run macOS applications
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

# lf - File manager with cd on exit
# Changes directory to last visited location when quitting lf
lf() {
  local tmp="$(mktemp)"
  command lf -last-dir-path="$tmp" "$@"
  if [ -f "$tmp" ]; then
    local dir="$(cat "$tmp")"
    rm -f "$tmp"
    if [ -d "$dir" ] && [ "$dir" != "$(pwd)" ]; then
      cd "$dir"
    fi
  fi
}

# assets - Copy asset from library to project folder (Wandelbots workflow)
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

# ============================================================================
# stow - chezmoi edit with fzf (opens source, then apply)
# ============================================================================
stow() {
  local file=$(chezmoi managed --include=files | \
        fzf --prompt="chezmoi edit: " \
            --preview='bat --color=always --style=numbers "$(chezmoi source-path "$HOME/{}")"' \
            --preview-window=right:60%:wrap)
  
  if [[ -z "$file" ]]; then
    return 1
  fi
  
  local source_path=$(chezmoi source-path ~/"$file")
  # Open in VS Code and wait until the file/editor window is closed
  code --wait "$source_path"
  
  # Automatically apply changes after editing
  if chezmoi apply; then
    echo "Applied chezmoi changes"
  else
    echo "chezmoi apply failed"
    return 1
  fi
  
  echo "Opened and applied: $source_path"
}
