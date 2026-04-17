if not vim.g.vscode then
  return {}
end

return {
  {
    "LazyVim/LazyVim",
    init = function()
      vim.api.nvim_create_autocmd({ "BufEnter", "WinEnter", "FileType" }, {
        group = vim.api.nvim_create_augroup("vscode_no_spell", { clear = true }),
        pattern = "*",
        callback = function()
          vim.wo.spell = false
        end,
      })
    end,
  },
}