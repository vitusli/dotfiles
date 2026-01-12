# ============================================================================
# CUSTOM FUNCTIONS
# ============================================================================

# / - Fuzzy find files/directories and open in Zed
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

  # Copy target to clipboard and open in Zed
  echo -n "$target" | pbcopy
  zed "$target"
  echo "Opened in Zed: $target"
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

# ============================================================================
# chezmoi-edit - chezmoi edit with fzf (opens source, then apply)
# ============================================================================
chezmoi-edit() {
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
