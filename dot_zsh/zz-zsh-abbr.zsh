# ============================================================================
# ZSH-ABBR
# ============================================================================

# Hardcode prefix to avoid slow `brew --prefix` subprocess on every shell start
if [[ "$OSTYPE" == darwin* ]]; then
  _abbr="/opt/homebrew/share/zsh-abbr/zsh-abbr.zsh"
else
  _abbr="/home/linuxbrew/.linuxbrew/share/zsh-abbr/zsh-abbr.zsh"
fi
[[ -f "$_abbr" ]] && source "$_abbr"
unset _abbr
