" VSCode Neovim Configuration
" Clipboard integration for macOS
set clipboard=unnamed

" Use system clipboard for yank, delete, change, and put operations
if has('clipboard')
    set clipboard=unnamed
    if has('unnamedplus')
        set clipboard=unnamed,unnamedplus
    endif
endif

" Additional settings for better VSCode integration
set ignorecase
set smartcase
set incsearch
set hlsearch
