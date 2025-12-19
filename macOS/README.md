# macOS Dotfiles

my macOS setup. install everything i need automatically.

## quick start

if the machine is new, download & run manually.

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macOS/macme.sh | zsh
```

## what it does (serious changes to your system)

the script (`macme.sh`) will:

- install xcode command line tools
- setup homebrew
- install all my apps & tools (brew formulae, casks, app store)
- setup github authentication & ssh keys
- clone my github repos
- apply macos system preferences (keyboard speed, animations, dock settings, etc.)
- apply dotfiles with chezmoi

it's idempotent, so you can run it multiple times safely. it only installs what's missing.

## chezmoi

dotfiles are managed with [chezmoi](https://www.chezmoi.io/). the source directory is `macOS/chezmoi/`.

### daily workflow

after editing files in `chezmoi/`, apply changes:

```bash
chezmoi apply
```

edit a managed file (opens source in editor):

```bash
chezmoi edit ~/.zshrc
```

or use the `stow` function (fuzzy-select with fzf):

```bash
stow   # select file, opens source in VS Code, copies 'chezmoi apply' to clipboard
```

### naming conventions

chezmoi uses prefixes to determine target paths:

- `dot_zshrc` → `~/.zshrc`
- `dot_config/` → `~/.config/`
- `literal_Application Support/` → `~/Library/Application Support/` (preserves spaces)
- `private_` prefix for files with restricted permissions

## logs

setup logs are saved to `~/dotfiles/logs/` for debugging if something goes wrong.

full list of apps in `macme.sh` under `FORMULAE`, `CASKS` and `MAS` arrays.

## system preferences

all macos defaults are configured in the `setup_system_defaults()` function. each setting has a comment explaining what it does.

## repos cloned

the script clones my private repositories. replace mine with your own in the `REPOS` array.

## github auth

during setup, you'll be prompted to authenticate with github via browser. this is needed for cloning private repos and using the github cli.

### note on VS Code custom CSS

the custom CSS extension requires a reload after every VS Code update. if your custom CSS isn't loading, run the **"Reload Custom CSS Extension"** command from the command palette (`⌘⇧P` > type "reload custom css").

### vim plugins (fzf, fzf.vim & wilder.nvim)

vim plugins are managed as git submodules in `macOS/chezmoi/dot_vim/pack/plugins/start/`. they're automatically initialized by the `macme.sh` setup script – no manual setup needed.

to manage plugins, use the plugin manager script:
- **install**: `~/dotfiles/macOS/chezmoi/dot_vim/plugin_manager.sh install` (or just `install`)
- **update**: `~/dotfiles/macOS/chezmoi/dot_vim/plugin_manager.sh update`
- **remove**: `~/dotfiles/macOS/chezmoi/dot_vim/plugin_manager.sh remove <plugin-name>`

## dotfiles documentation

here's what each dotfile/config does:

### shell configuration
- **`.zshrc`** - main zsh configuration, aliases, environment variables, prompt setup
- **`.zprofile`** - runs once at login, sets up PATH and login-time environment
- **`.profile`** - fallback profile for non-zsh shells
- **`.hushlogin`** - suppresses the "last login" message when opening terminal

### terminal & file managers
- **`.config/ghostty/config`** - ghostty terminal emulator configuration (fonts, colors, keybindings)
- **`.config/lf/lfrc`** - lf file manager configuration (vim-style navigation, preview, filters)
- **`.config/zsh-abbr/user-abbreviations`** - custom zsh abbreviations that expand as you type

### window management
- **`.aerospace.toml`** - aerospace window manager configuration (tiling, workspaces, keybindings)

### keyboard customization
- **`.config/karabiner/karabiner.json`** - karabiner-elements key remapping configuration
- **`.config/karabiner/assets/complex_modifications/`** - advanced karabiner modification rules
- **`Library/Keyboard Layouts/Roman.bundle/`** - custom US-German [keyboard layout](https://hci.rwth-aachen.de/usgermankeyboard)

### editors
- **`.config/nvim/init.vim`** - neovim text editor configuration
- **`.vimrc`** - vim text editor configuration
- **`.gvimrc`** - gvim (graphical vim) specific settings
- **`Library/Application Support/Code/User/settings.json`** - VS Code editor settings
- **`Library/Application Support/Code/User/keybindings.json`** - VS Code keyboard shortcuts
- **`Library/Application Support/Code/User/custom-vscode.css`** - VS Code custom CSS styling

### applications
- **`Library/Application Support/org.yanex.marta/conf.marco`** - marta file manager configuration
- **`Library/Application Support/org.yanex.marta/Themes/`** - custom themes for marta file manager
- **`Library/Application Support/com.mitchellh.ghostty/config`** - ghostty terminal configuration
- **`Library/Application Support/obsidian/Custom Dictionary.txt`** - obsidian custom dictionary

## feedback

if something breaks, check the logs
