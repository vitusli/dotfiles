# ============================================================================
# ZSH PLUGINS & COMPLETION
# ============================================================================

# Case-insensitive globbing and completion (like PowerShell)
unsetopt CASE_GLOB
unsetopt CASE_MATCH
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# Add brew completions to FPATH (macOS + WSL Ubuntu)
# Hardcode prefix to avoid slow `brew --prefix` subprocess on every shell start
if [[ "$OSTYPE" == darwin* ]] && [[ -d "/opt/homebrew/share/zsh/site-functions" ]]; then
  FPATH="/opt/homebrew/share/zsh/site-functions:${FPATH}"
elif [[ -n "$WSL_DISTRO_NAME" ]] && [[ -d "/home/linuxbrew/.linuxbrew/share/zsh/site-functions" ]]; then
  FPATH="/home/linuxbrew/.linuxbrew/share/zsh/site-functions:${FPATH}"
fi

# Load completion system only when omz did not initialize it yet.
if ! typeset -f _main_complete >/dev/null 2>&1; then
  autoload -Uz compinit
  compinit -C
fi

# Load nova completion (cached to avoid slow subprocess on every shell start)
_nova_comp_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/nova-completion.zsh"
if command -v nova &>/dev/null; then
  if [[ ! -f "$_nova_comp_cache" ]] || [[ "$(command -v nova)" -nt "$_nova_comp_cache" ]]; then
    mkdir -p "${_nova_comp_cache:h}"
    nova completion zsh >"$_nova_comp_cache" 2>/dev/null
  fi
  [[ -f "$_nova_comp_cache" ]] && source "$_nova_comp_cache"
fi
unset _nova_comp_cache

# Load chezmoi completion (cached to avoid slow subprocess on every shell start)
_chezmoi_comp_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/chezmoi-completion.zsh"
if command -v chezmoi &>/dev/null; then
  if [[ ! -f "$_chezmoi_comp_cache" ]] || [[ "$(command -v chezmoi)" -nt "$_chezmoi_comp_cache" ]]; then
    mkdir -p "${_chezmoi_comp_cache:h}"
    chezmoi completion zsh >"$_chezmoi_comp_cache" 2>/dev/null
  fi
  [[ -f "$_chezmoi_comp_cache" ]] && source "$_chezmoi_comp_cache"
fi
unset _chezmoi_comp_cache

# Configure completion menu
zstyle ':completion:*' menu select
