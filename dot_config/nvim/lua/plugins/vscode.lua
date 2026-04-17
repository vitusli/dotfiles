if not vim.g.vscode then
  return {}
end

return {
  {
    "LazyVim/LazyVim",
    init = function()
      vim.opt.spell = false
      vim.api.nvim_create_autocmd({ "BufEnter", "WinEnter", "FileType" }, {
        group = vim.api.nvim_create_augroup("vscode_spell", { clear = true }),
        callback = function()
          vim.wo.spell = false
        end,
      })
    end,
  },
}