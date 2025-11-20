set clipboard=unnamed

" Space in normal mode: fuzzy find and open in vim
nnoremap <Space> :call FuzzyFindAndOpen()<CR>

function! FuzzyFindAndOpen()
  " Select directory
  let dir = system('find ~ -type d 2>/dev/null | fzf --prompt="Select directory: " --preview="ls -la {}"')
  let dir = substitute(dir, '\n$', '', '')
  
  if empty(dir)
    return
  endif
  
  " Select file in directory
  let file = system('find "' . dir . '" -type f 2>/dev/null | fzf --prompt="Select file (or ESC for directory): " --preview="bat --color=always --style=numbers {}"')
  let file = substitute(file, '\n$', '', '')
  
  " If file selection was cancelled, abort completely
  if v:shell_error != 0
    return
  endif
  
  " Determine target
  let target = empty(file) ? dir : file
  
  " Copy to clipboard
  call system('echo -n "' . target . '" | pbcopy')
  
  " Open in vim
  execute 'edit ' . fnameescape(target)
  
  echo 'Opened and copied to clipboard: ' . target
endfunction

