# ============================================================================
# WINDOWS BOOTSTRAP SCRIPT (MODULAR)
# ============================================================================
# Modular bootstrap script that uses separate modules for each component.
# Each module handles its own verification instead of trusting exit codes.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/vitusli/dotfiles/main/windows.ps1 | powershell -c "$input | iex"
#
# Or with specific modules:
#   .\windows.ps1 -Packages -Registry
#   .\windows.ps1 -GitHub -Dotfiles
#   .\windows.ps1 -All
#   .\windows.ps1 -Help
# ============================================================================

#Requires -RunAsAdministrator

param(
    [switch]$Scoop,
    [switch]$Packages,
    [switch]$GitHub,
    [switch]$Dotfiles,
    [switch]$VSCode,
    [switch]$Registry,
    [switch]$Services,
    [switch]$Bloatware,
    [switch]$Features,
    [switch]$Defaults,
    [switch]$Status,
    [switch]$All,
    [switch]$Help
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ScriptDir = $PSScriptRoot
$LibDir = Join-Path $ScriptDir "lib"
$ModulesDir = Join-Path $ScriptDir "modules"

# Logging
$LOG_DIR = Join-Path $ScriptDir "logs"
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
$LOG_FILE = Join-Path $LOG_DIR "windows-setup-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Config
$CONFIG_URL = "https://raw.githubusercontent.com/vitusli/dotfiles/main/config"
$CONFIG_DIR = Join-Path $ScriptDir "config"

# Dotfiles
$DOTFILES_REPO = "vitusli/dotfiles"
$DOTFILES_BRANCH = "windows"

# Documents path (explicit English path)
$DOCUMENTS = "$HOME\Documents"

# ============================================================================
# LOAD LIBRARIES
# ============================================================================

. (Join-Path $LibDir "logging.ps1")
. (Join-Path $LibDir "config.ps1")

# ============================================================================
# HELP
# ============================================================================

function Show-Help
{
    $helpText = @"
Usage: .\windows.ps1 [OPTIONS]

If no options are provided, runs the full setup.

Options:
  -Scoop          Install Scoop package manager only
  -Packages       Install Scoop packages from config
  -GitHub         Setup GitHub auth & SSH key
  -Dotfiles       Apply dotfiles with chezmoi
  -VSCode         Install VS Code extensions
  -Registry       Apply registry tweaks
  -Services       Disable unnecessary services
  -Bloatware      Remove Windows bloatware
  -Features       Disable Windows features
  -Defaults       Apply system defaults
  -Status         Show current system status
  -All            Run full setup (same as no flags)
  -Help           Show this help message

Examples:
  .\windows.ps1 -Packages -Registry
  .\windows.ps1 -GitHub -Dotfiles
  .\windows.ps1 -Bloatware -Services
  .\windows.ps1 -Status
"@
    Write-Output $helpText
    exit 0
}

if ($Help)
{
    Show-Help
}

# ============================================================================
# DETERMINE RUN MODE
# ============================================================================

$SelectiveMode = $Scoop -or $Packages -or $GitHub -or $Dotfiles -or $VSCode -or `
    $Registry -or $Services -or $Bloatware -or $Features -or $Defaults -or $Status

function Should-Run
{
    param([string]$FlagName)

    if (-not $SelectiveMode -or $All)
    {
        return $true
    }

    switch ($FlagName)
    {
        "Scoop"
        { return $Scoop
        }
        "Packages"
        { return $Packages
        }
        "GitHub"
        { return $GitHub
        }
        "Dotfiles"
        { return $Dotfiles
        }
        "VSCode"
        { return $VSCode
        }
        "Registry"
        { return $Registry
        }
        "Services"
        { return $Services
        }
        "Bloatware"
        { return $Bloatware
        }
        "Features"
        { return $Features
        }
        "Defaults"
        { return $Defaults
        }
        default
        { return $false
        }
    }
}

# ============================================================================
# MODULE LOADING
# ============================================================================

function Load-Module
{
    param([string]$ModulePath)

    if (Test-Path $ModulePath)
    {
        . $ModulePath
        return $true
    } else
    {
        Log-Error "Module not found: $ModulePath"
        return $false
    }
}

# ============================================================================
# LOAD GITHUB MODULE
# ============================================================================

$GitHubModulePath = Join-Path $ModulesDir "github\auth.ps1"
if (Test-Path $GitHubModulePath)
{
    . $GitHubModulePath
} else
{
    Write-Warning "GitHub module not found at: $GitHubModulePath"
}

# ============================================================================
# LOAD DOTFILES MODULE
# ============================================================================

$DotfilesModulePath = Join-Path $ModulesDir "dotfiles\chezmoi.ps1"
if (Test-Path $DotfilesModulePath)
{
    . $DotfilesModulePath
} else
{
    Write-Warning "Dotfiles module not found at: $DotfilesModulePath"
}

# ============================================================================
# LOAD VSCODE MODULE
# ============================================================================

$VSCodeModulePath = Join-Path $ModulesDir "vscode\extensions.ps1"
if (Test-Path $VSCodeModulePath)
{
    . $VSCodeModulePath
} else
{
    Write-Warning "VSCode module not found at: $VSCodeModulePath"
}

# ============================================================================
# LOAD WINDOWS FEATURES MODULE
# ============================================================================

$FeaturesModulePath = Join-Path $ModulesDir "system\windows-features.ps1"
if (Test-Path $FeaturesModulePath)
{
    . $FeaturesModulePath
} else
{
    Write-Warning "Windows Features module not found at: $FeaturesModulePath"
}

# ============================================================================
# LOAD WINDOWS DEFAULTS MODULE
# ============================================================================

$DefaultsModulePath = Join-Path $ModulesDir "system\windows-defaults.ps1"
if (Test-Path $DefaultsModulePath)
{
    . $DefaultsModulePath
} else
{
    Write-Warning "Windows Defaults module not found at: $DefaultsModulePath"
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================

function Show-Status
{
    Log-Header "System Status"

    Write-Output ""
    Log-Info "=== Scoop ==="
    if (Get-Command scoop -ErrorAction SilentlyContinue)
    {
        $pkgCount = (scoop list 2>$null | Measure-Object).Count
        Log-Success "Scoop: installed ($pkgCount packages)"
    } else
    {
        Log-Warning "Scoop: not installed"
    }

    Write-Output ""
    Log-Info "=== GitHub ==="
    if (Verify-GHInstalled)
    {
        if (Verify-GHAuthenticated)
        {
            $user = & gh api user --jq '.login' 2>$null
            Log-Success "GitHub CLI: authenticated as $user"
        } else
        {
            Log-Warning "GitHub CLI: not authenticated"
        }
    } else
    {
        Log-Warning "GitHub CLI: not installed"
    }

    if (Test-Path "$HOME\.ssh\id_ed25519")
    {
        Log-Success "SSH key: exists"
    } else
    {
        Log-Warning "SSH key: not found"
    }

    Write-Output ""
    Log-Info "=== Dotfiles ==="
    if (Verify-ChezmoiInstalled)
    {
        Log-Success "chezmoi: installed"
        if (Test-Path "$HOME\.local\share\chezmoi\.git")
        {
            Push-Location "$HOME\.local\share\chezmoi"
            $branch = git rev-parse --abbrev-ref HEAD 2>$null
            Pop-Location
            Log-Success "chezmoi initialized: branch $branch"
        } else
        {
            Log-Warning "chezmoi: not initialized"
        }
    } else
    {
        Log-Warning "chezmoi: not installed"
    }

    Write-Output ""
    Log-Info "=== VS Code ==="
    if (Verify-VSCodeInstalled)
    {
        $extCount = (@(& code --list-extensions 2>$null)).Count
        Log-Success "VS Code: installed ($extCount extensions)"
    } else
    {
        Log-Warning "VS Code: not installed"
    }

    Write-Output ""
    Log-Info "=== Windows ==="
    Log-Info "Version: $([System.Environment]::OSVersion.VersionString)"

    $theme = Get-ItemPropertyValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" -Name "AppsUseLightTheme" -ErrorAction SilentlyContinue
    if ($theme -eq 0)
    {
        Log-Success "Theme: Dark mode"
    } else
    {
        Log-Info "Theme: Light mode"
    }
}

# ============================================================================
# MAIN
# ============================================================================

function Main
{
    # Initialize logging
    Initialize-Logging

    # Handle status flag specially
    if ($Status)
    {
        Show-Status
        exit 0
    }

    # Show intro
    Write-Output "════════════════════════════════════════════════════════════"
    Write-Output "  Windows Setup Script (Modular)"
    Write-Output "  For Design/Dev Workflow"
    Write-Output "════════════════════════════════════════════════════════════"
    Write-Output ""
    Log-Info "Log file: $LOG_FILE"
    Write-Output ""

    if ($SelectiveMode -and -not $All)
    {
        Log-Info "Running in selective mode"
    } else
    {
        Log-Info "Running full setup"
        Write-Output ""
        Write-Output "This script will:"
        Write-Output "  - Install Scoop + packages"
        Write-Output "  - Setup GitHub authentication"
        Write-Output "  - Apply dotfiles via chezmoi"
        Write-Output "  - Install VS Code extensions"
        Write-Output "  - Remove bloatware"
        Write-Output "  - Apply registry tweaks"
        Write-Output "  - Disable unnecessary services"
        Write-Output ""
        Read-Host "Press Enter to continue or Ctrl+C to abort"
    }

    $errors = 0

    # ========================================
    # SCOOP
    # ========================================
    if (Should-Run "Scoop" -or Should-Run "Packages")
    {
        Load-Module (Join-Path $ModulesDir "packages\scoop.ps1")
        if (-not (Install-Scoop))
        { $errors++
        }
        if (-not (Add-ScoopBuckets))
        { $errors++
        }
    }

    # ========================================
    # PACKAGES
    # ========================================
    if (Should-Run "Packages")
    {
        Load-Module (Join-Path $ModulesDir "packages\scoop.ps1")
        if (-not (Install-ScoopPackages))
        { $errors++
        }
    }

    # ========================================
    # GITHUB
    # ========================================
    if (Should-Run "GitHub")
    {
        if (-not (Setup-GitConfig))
        { $errors++
        }
        if (-not (Setup-GitHubAuth))
        { $errors++
        }
        if (-not (Setup-SSHKey))
        { $errors++
        }
        Clone-Repositories | Out-Null
    }

    # ========================================
    # DOTFILES
    # ========================================
    if (Should-Run "Dotfiles")
    {
        if (-not (Setup-Dotfiles))
        { $errors++
        }
    }

    # ========================================
    # VSCODE
    # ========================================
    if (Should-Run "VSCode")
    {
        if (-not (Install-VSCodeExtensions))
        { $errors++
        }
    }

    # ========================================
    # BLOATWARE
    # ========================================
    if (Should-Run "Bloatware")
    {
        Load-Module (Join-Path $ModulesDir "system\windows-bloatware.ps1")
        if (-not (Remove-Bloatware))
        { $errors++
        }
    }

    # ========================================
    # SERVICES
    # ========================================
    if (Should-Run "Services")
    {
        Load-Module (Join-Path $ModulesDir "system\windows-services.ps1")
        if (-not (Setup-Services))
        { $errors++
        }
    }

    # ========================================
    # REGISTRY
    # ========================================
    if (Should-Run "Registry")
    {
        Load-Module (Join-Path $ModulesDir "system\windows-registry.ps1")
        if (-not (Setup-RegistryTweaks))
        { $errors++
        }
    }

    # ========================================
    # FEATURES
    # ========================================
    if (Should-Run "Features")
    {
        Disable-WindowsFeatures | Out-Null
    }

    # ========================================
    # DEFAULTS
    # ========================================
    if (Should-Run "Defaults")
    {
        Apply-SystemDefaults | Out-Null
    }

    # ========================================
    # SUMMARY
    # ========================================
    Log-Header "Setup Complete!"
    Write-Output ""

    if ($errors -gt 0)
    {
        Log-Warning "Completed with $errors issues - check log for details"
    } else
    {
        Log-Success "All tasks completed successfully!"
    }

    Write-Output ""
    Write-Output "════════════════════════════════════════════════════════════"
    Write-Output "  Next steps:"
    Write-Output "════════════════════════════════════════════════════════════"
    Write-Output ""
    Write-Output "  1. Restart your computer to apply all changes"
    Write-Output ""
    Write-Output "  2. Sign into apps as needed"
    Write-Output ""
    Write-Output "  Log file: $LOG_FILE"
    Write-Output ""
}

# Run main
try
{
    Main
} catch
{
    Log-Error "Fatal error: $_"
    exit 1
}
