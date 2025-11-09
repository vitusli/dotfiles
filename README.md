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

the script symlinks configuration files from the `/stow` directory to your home directory using `stow`.

## feedback

if something breaks, check the logs
