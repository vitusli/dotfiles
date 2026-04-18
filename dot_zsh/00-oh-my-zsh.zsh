# ============================================================================
# OH-MY-ZSH + FZF CLIPBOARD BINDING
# ============================================================================

# oh-my-zsh
export ZSH="$HOME/.oh-my-zsh"
export ZSH_THEME=""

plugins=(
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# Ensure external omz plugins exist on macOS and WSL Ubuntu.
if [[ -d "$ZSH" ]] && command -v git >/dev/null 2>&1; then
  export ZSH_CUSTOM="${ZSH_CUSTOM:-$ZSH/custom}"
  [[ -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]] || git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions" >/dev/null 2>&1
  [[ -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]] || git clone https://github.com/zsh-users/zsh-syntax-highlighting "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" >/dev/null 2>&1
fi

if [[ -r "$ZSH/oh-my-zsh.sh" ]]; then
  source "$ZSH/oh-my-zsh.sh"
fi
