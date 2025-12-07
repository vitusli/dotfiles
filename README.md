# dotfiles

my macOS setup. install everything i need automatically.

## quick start

if the machine is new, download & run manually.

```bash
curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/macme.sh | zsh
```

## what it does

the script (`macme.sh`) will:

- install xcode command line tools
- setup homebrew
- install all my apps & tools (brew formulae, casks, app store)
- setup github authentication & ssh keys
- clone my github repos
- apply macos system preferences (keyboard speed, animations, dock settings, etc.)
- stow dotfiles from this repository for configs

it's idempotent, so you can run it multiple times safely. it only installs what's missing.

## logs

setup logs are saved to `~/dotfiles/logs/` for debugging if something goes wrong.

full list of apps in `macme.sh` under `FORMULAE`, `CASKS` and `MAS` arrays.

## system preferences

all macos defaults are configured in the `setup_system_defaults()` function. each setting has a comment explaining what it does.

## repos cloned

the script clones my private repositories. replace mine with your own in the `REPOS` array.

## github auth

during setup, you'll be prompted to authenticate with github via browser. this is needed for cloning private repos and using the github cli.

## stow

the script symlinks configuration files from the `/stow` directory to your home directory using `stow`. underneath is a list of what each config does.

### vim plugins (fzf & fzf.vim)

these plugins are vendored directly in the repo at `stow/.vim/pack/plugins/start/`. they're installed automatically when you run `stow` – no separate setup needed.

they're stable and rarely need updates. to update manually (optional, maybe years later or in case something is broken):

```bash
cd ~/dotfiles/stow/.vim/pack/plugins/start

# Remove old versions
rm -rf fzf fzf.vim

# Clone fresh, then remove .git to vendor them
git clone --depth 1 https://github.com/junegunn/fzf.git
git clone --depth 1 https://github.com/junegunn/fzf.vim.git
rm -rf fzf/.git fzf.vim/.git

# Commit the updated files
cd ~/dotfiles
git add -f stow/.vim/pack/plugins/start/fzf stow/.vim/pack/plugins/start/fzf.vim
git commit -m "update: vim plugins fzf + fzf.vim"
git push
```

## dotfiles documentation

here's what each dotfile/config does:

### shell configuration
- **`.zshrc`** - main zsh configuration, aliases, environment variables, prompt setup
- **`.zprofile`** - runs once at login, sets up PATH and login-time environment
- **`.profile`** - fallback profile for non-zsh shells
- **`.hushlogin`** - suppresses the "last login" message when opening terminal

### terminal & multiplexer
- **`.config/alacritty.toml`** - alacritty terminal emulator configuration (fonts, colors, keybindings)
- **`.config/zellij/config.kdl`** - zellij terminal multiplexer config (alternative to tmux)
- **`.config/zsh-abbr/user-abbreviations`** - custom zsh abbreviations that expand as you type

### window management
- **`.aerospace.toml`** - aerospace window manager configuration (tiling, workspaces, keybindings)

### keyboard customization
- **`.config/karabiner/karabiner.json`** - karabiner-elements key remapping configuration
- **`.config/karabiner/assets/complex_modifications/`** - advanced karabiner modification rules
- **`Library/Keyboard Layouts/Roman.bundle/`** - custom US-German [keyboard layout](https://hci.rwth-aachen.de/usgermankeyboard)

### editors
- **`.vimrc`** - vim text editor configuration
- **`.gvimrc`** - gvim (graphical vim) specific settings
- **`Library/Application Support/Code/User/settings.json`** - VS Code editor settings
- **`Library/Application ort/Code/User/keybindings.json`** - VS Code keyboard shortcuts

### applications
- **`Library/Application Support/org.yanex.marta/conf.marco`** - marta file manager configuration
- **`Library/Application Support/org.yanex.marta/Themes/`** - custom themes for marta file manager

## feedback

if something breaks, check the logs
