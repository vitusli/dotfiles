# ============================================================================
# CUSTOM FUNCTIONS (Linux / WSL)
# ============================================================================

# Clipboard helper for WSL/Linux
_clipboard_copy() {
  if command -v clip.exe &>/dev/null; then
    # WSL: use Windows clip.exe
    cat | clip.exe
  elif command -v xclip &>/dev/null; then
    cat | xclip -selection clipboard
  elif command -v xsel &>/dev/null; then
    cat | xsel --clipboard --input
  else
    cat > /dev/null  # silently discard if no clipboard available
  fi
}

# / - Fuzzy find files/directories and open in VS Code
# Usage: /
/() {
  local search_dirs=(~/Downloads ~/Documents ~/Desktop ~/.local/share/chezmoi ~/codespace)
  local home_depth=3
  
  # Build find command
  local find_cmd=""
  if [[ ${#search_dirs[@]} -gt 0 ]]; then
    find_cmd="find ${search_dirs[@]} 2>/dev/null"
  fi
  if [[ $home_depth -gt 0 ]]; then
    [[ -n $find_cmd ]] && find_cmd="$find_cmd; "
    find_cmd="${find_cmd}find ~ -maxdepth $home_depth 2>/dev/null"
  fi
  
  # Pick target file/dir
  local target=$(eval "{ $find_cmd; }" | fzf --prompt=": " \
        --preview='[[ -f {} ]] && bat --color=always --style=numbers {} 2>/dev/null || ls -la {}' \
        --preview-window=right:60%:wrap)
  
  local fzf_exit=$?
  if [[ $fzf_exit -eq 130 ]] || [[ -z $target ]]; then
    return $fzf_exit
  fi
  
  # Copy target to clipboard and open in VS Code
  echo -n "$target" | _clipboard_copy
  code "$target"
  echo "Opened in VS Code: $target"
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
# stow - chezmoi edit with fzf (opens source, then apply)
# ============================================================================
stow() {
  local file=$(chezmoi managed --include=files | \
        fzf --prompt="chezmoi edit: " \
            --preview='bat --color=always --style=numbers "$(chezmoi source-path "$HOME/{}")" 2>/dev/null' \
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
