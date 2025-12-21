-- WezTerm Configuration
-- Ported from Ghostty config with Windows-specific keybindings

local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- ==========================
-- Font
-- ==========================
config.font_size = 12.0

-- ==========================
-- Window Appearance
-- ==========================
config.window_decorations = "RESIZE"  -- Window decorations enabled
config.window_padding = {
  left = 18,
  right = 18,
  top = 16,
  bottom = 16,
}

-- Background
config.window_background_opacity = 1.0

-- Windows-specific: Acrylic blur effect
config.win32_system_backdrop = 'Acrylic'

-- ==========================
-- Colors (CursorDarkMidnight theme)
-- ==========================
config.colors = {
  -- Background and foreground
  background = '#191c22',
  foreground = '#7b88a1',
  
  -- Cursor
  cursor_bg = '#8fbcbb',
  cursor_fg = '#191c22',
  cursor_border = '#8fbcbb',
  
  -- Selection
  selection_bg = '#21242b',
  selection_fg = '#7b88a1',
  
  -- Normal colors
  ansi = {
    '#3b4252', -- black
    '#bf616a', -- red
    '#a3be8c', -- green
    '#ebcb8b', -- yellow
    '#81a1c1', -- blue
    '#b48ead', -- magenta
    '#88c0d0', -- cyan
    '#e5e9f0', -- white
  },
  
  -- Bright colors
  brights = {
    '#4c566a', -- bright black
    '#bf616a', -- bright red
    '#a3be8c', -- bright green
    '#ebcb8b', -- bright yellow
    '#81a1c1', -- bright blue
    '#b48ead', -- bright magenta
    '#8fbcbb', -- bright cyan
    '#eceff4', -- bright white
  },
}

-- ==========================
-- Tab Bar
-- ==========================
config.enable_tab_bar = true
config.hide_tab_bar_if_only_one_tab = false
config.use_fancy_tab_bar = true

-- ==========================
-- Keybindings (Windows-optimized)
-- ==========================
-- Note: On Windows, we use CTRL instead of CMD for consistency with Windows conventions

config.keys = {
  -- Split Navigation - Ctrl + Shift + h/j/k/l
  -- Navigate to left pane
  {
    key = 'h',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.ActivatePaneDirection 'Left',
  },
  -- Navigate to bottom pane
  {
    key = 'j',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.ActivatePaneDirection 'Down',
  },
  -- Navigate to top pane
  {
    key = 'k',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.ActivatePaneDirection 'Up',
  },
  -- Navigate to right pane
  {
    key = 'l',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.ActivatePaneDirection 'Right',
  },
  
  -- New Split - Ctrl + n (split right), Ctrl + Shift + n (split down)
  {
    key = 'n',
    mods = 'CTRL',
    action = wezterm.action.SplitPane {
      direction = 'Right',
      size = { Percent = 50 },
    },
  },
  {
    key = 'n',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.SplitPane {
      direction = 'Down',
      size = { Percent = 50 },
    },
  },
  
  -- Equalize Splits - Ctrl + Shift + e
  {
    key = 'e',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.Multiple {
      wezterm.action.AdjustPaneSize { 'Left', 100 },
      wezterm.action.AdjustPaneSize { 'Right', 100 },
      wezterm.action.AdjustPaneSize { 'Up', 100 },
      wezterm.action.AdjustPaneSize { 'Down', 100 },
    },
  },
  
  -- Toggle Pane Zoom - Ctrl + Space
  {
    key = ' ',
    mods = 'CTRL',
    action = wezterm.action.TogglePaneZoomState,
  },
  
  -- Tab Management
  -- New Tab - Ctrl + t
  {
    key = 't',
    mods = 'CTRL',
    action = wezterm.action.SpawnTab 'CurrentPaneDomain',
  },
  -- Close Pane (or Tab if last pane) - Ctrl + w
  {
    key = 'w',
    mods = 'CTRL',
    action = wezterm.action.CloseCurrentPane { confirm = false },
  },
  -- Switch to next tab - Ctrl + Tab
  {
    key = 'Tab',
    mods = 'CTRL',
    action = wezterm.action.ActivateTabRelative(1),
  },
  -- Switch to previous tab - Ctrl + Shift + Tab
  {
    key = 'Tab',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.ActivateTabRelative(-1),
  },
}

-- ==========================
-- Additional Settings
-- ==========================
-- Unzoom when switching panes
config.unzoom_on_switch_pane = true

-- Scrollback
config.scrollback_lines = 10000

-- Default program (PowerShell on Windows)
config.default_prog = { 'pwsh.exe', '-NoLogo' }

return config
