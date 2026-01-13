# Enable tab completion for Winget
try {
    Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
        param($wordToComplete, $commandAst, $compPoint)
        winget complete --word $wordToComplete --commandline $commandAst.ToString() --position $compPoint |
            ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
    }
} catch {
    Write-Verbose "Winget completion registration failed: $($_.Exception.Message)"
}

# Enable tab completion for chezmoi
try {
    chezmoi completion powershell | Out-String | Invoke-Expression
} catch {
    Write-Verbose "Chezmoi completion registration failed: $($_.Exception.Message)"
}

# Add scoop to PATH
$env:Path = "C:\Users\Vitus\scoop\shims;$env:Path"

# fzf: Copy result to clipboard on Enter (in addition to normal output)
$env:FZF_DEFAULT_OPTS = "--bind 'enter:execute-silent(powershell -nop -c Set-Clipboard {})+accept'"

# Module Management
# Automatically install and import required modules
$requiredModules = @('PSReadLine', 'ZLocation')
foreach ($module in $requiredModules) {
    if (-not (Get-Module -ListAvailable -Name $module)) {
        Write-Host "Installing $module..."
        Install-Module $module -Scope CurrentUser -Force
    }
    Import-Module $module
}

# Define ViModeChange handler FIRST
$OnViModeChange = [scriptblock]{
   if ($args[0] -eq 'Command') {
       # Set the cursor to a blinking block.
       Write-Host -NoNewLine "`e[2 q"
   }
   else {
       # Set the cursor to a line.
       Write-Host -NoNewLine "`e[6 q"
   }
}

# THEN enable Vim with the handler
Set-PsReadLineOption -EditMode Vi
Set-PSReadLineOption -ViModeIndicator Script -ViModeChangeHandler $OnViModeChange

# MenuComplete AFTER Vi mode (Vi mode overrides Tab binding)
Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete

# Set the initial cursor to a line for Insert Mode
Write-Host -NoNewLine "`e[6 q"

# Reset cursor to line after every command (like zsh zle-line-init)
$PSDefaultParameterValues['Out-Default:OutVariable'] = '__lastOutput'
Set-PSReadLineOption -ExtraPromptLineCount 0
$function:prompt = {
    # Reset cursor to line for Insert Mode after every command
    Write-Host -NoNewLine "`e[6 q"
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}

# Abbreviations - expand on Space
$Abbreviations = @{
    'p'   = 'uv run python'
    'c' = 'chezmoi'
    'ov'  = 'A:\isaac-sim\isaac-sim.bat'
    'l'   = 'lazygit'
    'rl' = '. $PROFILE'
    'ahk' = 'Get-Process | Where-Object {$_.Name -like "*AutoHotkey*"} | Stop-Process -Force; Start-Process "c:\Users\Vitus\wotfiles\ahkv1\macish.ahk"'
    'zf' = '$f = Get-ChildItem -File -Recurse | ForEach-Object { $_.FullName } | fzf; if ($f) { Set-Location (Split-Path $f) }'
    '..' = 'Set-Location ..\..'
    '...' = 'Set-Location ..\..\..'
}

Set-PSReadLineKeyHandler -Key ' ' -ScriptBlock {
    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    $tokens = $line -split '\s+'
    $firstToken = $tokens[0]

    if ($Abbreviations.ContainsKey($firstToken)) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $firstToken.Length, $Abbreviations[$firstToken])
    }
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert(' ')
}

Set-PSReadLineKeyHandler -Key 'Enter' -ScriptBlock {
    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    $tokens = $line -split '\s+'
    $firstToken = $tokens[0]

    if ($Abbreviations.ContainsKey($firstToken)) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $firstToken.Length, $Abbreviations[$firstToken])
    }
    [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
}

# Scoop completion (installed via scoop, per Moeologist README)
try {
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        $scoopRoot = (Get-Item (Get-Command scoop.ps1).Path).Directory.Parent.FullName
        $modulePath = Join-Path $scoopRoot 'modules\scoop-completion'
        if (Test-Path $modulePath) {
            Import-Module $modulePath -ErrorAction Stop
        } else {
            Write-Verbose "scoop-completion module path not found: $modulePath"
        }
    }
} catch {
    Write-Verbose "Scoop completion load failed: $($_.Exception.Message)"
}

# gsudo module (enables `gsudo !!` to elevate last command)
Import-Module gsudoModule -ErrorAction SilentlyContinue

# ============================================================================
# stow - chezmoi edit with fzf (opens source, then apply)
# ============================================================================
function stow {
    $file = chezmoi managed --include=files | fzf --prompt="chezmoi edit: "
    if ($file) {
        $sourcePath = chezmoi source-path $HOME\$file
        code $sourcePath
        Set-Clipboard -Value "chezmoi apply"
        Write-Host "Opened: $sourcePath"
        Write-Host "'chezmoi apply' copied to clipboard"
    }
}

# ============================================================================
# / - Fuzzy find files/directories and open in VS Code
# ============================================================================
function / {
    # Search directories
    $searchDirs = @(
        "$HOME\Downloads",
        "$HOME\Documents",
        "$HOME\Desktop",
        "$HOME\.local\share\chezmoi",
        "$HOME\codespace",
        "$HOME\wotfiles"
    )
    $homeDepth = 3

    # Use fd for fast file finding, fallback to Get-ChildItem if fd not available
    if (Get-Command fd -ErrorAction SilentlyContinue) {
        $target = & {
            foreach ($dir in $searchDirs) {
                if (Test-Path $dir) {
                    fd . $dir --type f --type d 2>$null
                }
            }
            fd . $HOME --max-depth $homeDepth --type f --type d 2>$null
        } | fzf --prompt=": " --preview="if (Test-Path -PathType Leaf '{}') { bat --color=always --style=numbers '{}' } else { Get-ChildItem '{}' }" --preview-window="right:60%:wrap"
    } else {
        $target = & {
            foreach ($dir in $searchDirs) {
                if (Test-Path $dir) {
                    Get-ChildItem -Path $dir -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
                }
            }
            Get-ChildItem -Path $HOME -Depth $homeDepth -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
        } | fzf --prompt=": "
    }

    if ([string]::IsNullOrEmpty($target)) {
        return
    }

    Set-Clipboard -Value $target
    code $target
    Write-Host "Opened in VS Code: $target"
}
