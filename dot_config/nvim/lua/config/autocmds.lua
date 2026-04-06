-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)

-- In VS Code: disable Neovim spell check (cSpell handles it)
if vim.g.vscode then
  vim.api.nvim_create_autocmd({ "BufEnter", "WinEnter" }, {
    group = vim.api.nvim_create_augroup("vscode_no_spell", { clear = true }),
    pattern = "*",
    callback = function()
      vim.opt_local.spell = false
    end,
  })
end
