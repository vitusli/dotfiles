# ============================================================================
# VIM MODE
# ============================================================================

# Enable vim bindings
bindkey -v

# Speed up vim mode - reduce escape key delay
export KEYTIMEOUT=1

# Cursor shape for vi mode (block in normal, line in insert)
function zle-keymap-select() {
    case $KEYMAP in
        vicmd)       print -n "\e[2 q" ;;  # Block cursor for normal mode
        main|viins|*) print -n "\e[6 q" ;;  # Line cursor for insert mode
    esac
}

function zle-line-init() {
    print -n "\e[6 q"  # Start with line cursor (insert mode)
}

zle -N zle-keymap-select
zle -N zle-line-init

# ============================================================================
# VIM MODE CLIPBOARD INTEGRATION
# ============================================================================

# Copy vim yank operations to system clipboard on macOS and Linux/WSL.
# Wraps widgets AFTER plugin loading to call builtin versions with leading dot
_copy_cutbuffer_to_clipboard() {
    [[ -z $CUTBUFFER ]] && return

    if [[ "$OSTYPE" == darwin* ]] && command -v pbcopy >/dev/null 2>&1; then
        printf '%s' "$CUTBUFFER" | pbcopy
    elif [[ -n "$WSL_DISTRO_NAME" ]] && command -v wl-copy >/dev/null 2>&1; then
        printf '%s' "$CUTBUFFER" | wl-copy
    fi
}

vi_yank_wrapper() { zle .vi-yank; _copy_cutbuffer_to_clipboard }
vi_yank_whole_line_wrapper() { zle .vi-yank-whole-line; _copy_cutbuffer_to_clipboard }
vi_yank_eol_wrapper() { zle .vi-yank-eol; _copy_cutbuffer_to_clipboard }

zle -N vi-yank vi_yank_wrapper
zle -N vi-yank-whole-line vi_yank_whole_line_wrapper
zle -N vi-yank-eol vi_yank_eol_wrapper
