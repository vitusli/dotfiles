# ============================================================================
# VIM MODE
# ============================================================================

# Enable vim bindings
bindkey -v

# Speed up vim mode - reduce escape key delay
export KEYTIMEOUT=1

# Cursor shape for vi mode (block in normal, line in insert)
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

zle -N zle-keymap-select
zle -N zle-line-init

# ============================================================================
# VIM MODE CLIPBOARD INTEGRATION (WSL)
# ============================================================================

# Copy vim yank operations to Windows/WSL clipboard
# Uses clip.exe which is available in WSL
_copy_cutbuffer_to_clipboard() {
  if [[ -n $CUTBUFFER ]]; then
    if command -v clip.exe &>/dev/null; then
      # WSL: use Windows clip.exe
      printf '%s' "$CUTBUFFER" | clip.exe
    elif command -v xclip &>/dev/null; then
      # Native Linux with X11
      printf '%s' "$CUTBUFFER" | xclip -selection clipboard
    elif command -v xsel &>/dev/null; then
      # Alternative X11 clipboard
      printf '%s' "$CUTBUFFER" | xsel --clipboard --input
    fi
  fi
}

vi_yank_wrapper() { zle .vi-yank; _copy_cutbuffer_to_clipboard }
vi_yank_whole_line_wrapper() { zle .vi-yank-whole-line; _copy_cutbuffer_to_clipboard }
vi_yank_eol_wrapper() { zle .vi-yank-eol; _copy_cutbuffer_to_clipboard }

zle -N vi-yank vi_yank_wrapper
zle -N vi-yank-whole-line vi_yank_whole_line_wrapper
zle -N vi-yank-eol vi_yank_eol_wrapper
