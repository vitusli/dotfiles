if not vim.g.vscode then
  return {}
end

local function disable_vscode_rendering(args)
  local get_clients = vim.lsp.get_clients or vim.lsp.get_active_clients

  vim.bo[args.buf].spell = false
  vim.bo[args.buf].syntax = ""
  pcall(vim.treesitter.stop, args.buf)

  for _, client in ipairs(get_clients({ bufnr = args.buf })) do
    client.server_capabilities.semanticTokensProvider = nil
  end
end

return {
  {
    "LazyVim/LazyVim",
    init = function()
      vim.cmd("syntax off")
      vim.diagnostic.enable(false)

      vim.api.nvim_create_autocmd({ "BufEnter", "BufWinEnter", "FileType", "LspAttach", "WinEnter" }, {
        group = vim.api.nvim_create_augroup("vscode_clean_rendering", { clear = true }),
        callback = disable_vscode_rendering,
      })
    end,
  },
  {
    "nvim-treesitter/nvim-treesitter",
    enabled = false,
  },
  {
    "nvim-treesitter/nvim-treesitter-textobjects",
    enabled = false,
  },
  {
    "JoosepAlviste/nvim-ts-context-commentstring",
    enabled = false,
  },
  {
    "folke/ts-comments.nvim",
    enabled = false,
  },
}