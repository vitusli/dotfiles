set clipboard=unnamed

" fzf.vim konfiguration
set rtp+=/opt/homebrew/bin/fzf

" Space: Begrenzte Suche in wichtigen Verzeichnissen (wie in .zshrc)
" Durchsucht: Downloads, Documents, Desktop, dotfiles + Home (max depth 3)
nnoremap <Space> :call fzf#run(fzf#wrap({'source': 'find ~/Downloads ~/Documents ~/Desktop ~/dotfiles -maxdepth 10 2>/dev/null; find ~ -maxdepth 3 2>/dev/null', 'sink': 'e'}))<CR>
