set clipboard=unnamed

" fzf.vim konfiguration
set rtp+=/opt/homebrew/bin/fzf

" Space: Begrenzte Suche in wichtigen Verzeichnissen (wie in .zshrc)
" Durchsucht: Downloads, Documents, Desktop, dotfiles + Home (max depth 3)
nnoremap <Space> :call fzf#run(fzf#wrap({'source': 'find ~/Downloads ~/Documents ~/Desktop ~/dotfiles -maxdepth 10 2>/dev/null; find ~ -maxdepth 3 2>/dev/null', 'sink': 'e'}))<CR>

" Relative line numbers (plus absolute cursor line)
set number
set relativenumber

" Reduce ESC delay (similar to Zsh KEYTIMEOUT)
set ttimeout
set ttimeoutlen=10   " time to wait for terminal key codes (ESC sequences)
set timeoutlen=300   " mapping timeout; keep reasonable for sequences

" Cursor Shape (Terminal Vim) passend zu Zsh vi-mode
" Normal mode: Block, Insert mode: Beam, Replace: Underline
let &t_EI = "\e[2 q"
let &t_SI = "\e[6 q"
let &t_SR = "\e[4 q"

augroup CursorShape
	autocmd!
	autocmd VimEnter,InsertLeave * silent! let &t_EI = "\e[2 q"
	autocmd InsertEnter          * silent! let &t_SI = "\e[6 q"
	autocmd ModeChanged *:[vVsS] silent! if mode() !~# '^[iR]' | let &t_EI = "\e[2 q" | endif
augroup END
