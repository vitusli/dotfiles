-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)

-- In VS Code: disable Tree-Sitter and other UI features that cause rendering issues
-- VS Code has its own syntax highlighting and features - we only want Neovim keybindings & plugins like mini.surround
if vim.g.vscode then
  -- Disable Tree-Sitter highlighting (causes artifacts/double text)
  vim.opt.syntax = "off"
  
  -- Disable Tree-Sitter completely
  vim.treesitter.stop()
  
  -- Disable spell check (cSpell handles it in VS Code)
  vim.api.nvim_create_autocmd({ "BufEnter", "WinEnter" }, {
    group = vim.api.nvim_create_augroup("vscode_no_spell", { clear = true }),
    pattern = "*",
    callback = function()
      vim.opt_local.spell = false
    end,
  })
end
