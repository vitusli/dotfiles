# duti – Default Applications Configuration

`duti` is a CLI tool to set default applications for file types and UTIs system-wide on macOS.

## Setup

The `duti` formula is installed automatically by `macme.sh`. During setup, the configuration from `duti/duti` is applied via the `duti/set-defaults.sh` script:

```zsh
./duti/set-defaults.sh
```

This runs `duti -s` for each line in `duti/duti` and sets all file type associations persistently in the system.

## Configuration

Edit `duti/duti` to add, remove, or modify file type associations.

**Format:** Each line is `bundle_id|file_type_or_uti|role`

```
com.microsoft.VSCode|.py|all
org.yanex.marta|public.folder|all
```

### Finding Bundle IDs

```zsh
mdls -name kMDItemCFBundleIdentifier /Applications/AppName.app
```

### Common UTIs

- `public.plain-text` – text files
- `public.shell-script` – shell scripts
- `public.python-script` – Python files
- `public.folder` – folders/directories
- `.sh`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.md`, `.txt` – file extensions

## Roles

- `all` – both viewer and editor (default)
- `viewer` – open with (view only)
- `editor` – edit with

## Manual Application

To apply changes after editing `duti/duti`:

```zsh
~/dotfiles/duti/set-defaults.sh
```

## Verify Current Settings

```zsh
duti d <file_type>  # Show current default for a file type
```

Example:
```zsh
duti d .py          # Show default app for Python files
duti d public.folder  # Show default app for folders
```
