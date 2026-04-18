# ============================================================================
# ZSH PLUGINS (no Oh-My-Zsh overhead)
# ============================================================================

# zsh-autosuggestions
if [[ "$OSTYPE" == darwin* ]]; then
  _zas="/opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
else
  _zas="/home/linuxbrew/.linuxbrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
fi
[[ -f "$_zas" ]] && source "$_zas"
unset _zas

# zsh-syntax-highlighting
if [[ "$OSTYPE" == darwin* ]]; then
  _zsh_hl="/opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
else
  _zsh_hl="/home/linuxbrew/.linuxbrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi
[[ -f "$_zsh_hl" ]] && source "$_zsh_hl"
unset _zsh_hl
