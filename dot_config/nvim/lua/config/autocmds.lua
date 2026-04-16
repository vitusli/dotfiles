-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)

-- In VS Code: keep editing plugins, but disable Neovim rendering/highlighting features.
-- VS Code should be the single source of syntax/diagnostics UI to avoid flicker/artifacts.
if vim.g.vscode then
  local get_clients = vim.lsp.get_clients or vim.lsp.get_active_clients

  -- Turn off global Vim syntax engine immediately.
  vim.cmd("syntax off")

  -- Disable Neovim diagnostics UI. VS Code diagnostics remain active.
  vim.diagnostic.enable(false)

  local group = vim.api.nvim_create_augroup("vscode_clean_rendering", { clear = true })
  vim.api.nvim_create_autocmd({ "BufEnter", "WinEnter", "FileType", "LspAttach" }, {
    group = group,
    pattern = "*",
    callback = function(args)
      vim.opt_local.spell = false
      vim.bo[args.buf].syntax = ""
      pcall(vim.treesitter.stop, args.buf)

      for _, client in ipairs(get_clients({ bufnr = args.buf })) do
        client.server_capabilities.semanticTokensProvider = nil
      end
    end,
  })
end
