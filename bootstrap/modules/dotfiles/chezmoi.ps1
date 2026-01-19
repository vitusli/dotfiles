# ============================================================================
# CHEZMOI DOTFILES MODULE
# Handles dotfiles management with chezmoi for Windows
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Info -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}

if (-not (Get-Command Load-Config -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "config.ps1")
}

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default dotfiles repository
if (-not $env:DOTFILES_REPO)
{
    $script:DOTFILES_REPO = "vitusli/dotfiles"
} else
{
    $script:DOTFILES_REPO = $env:DOTFILES_REPO
}

if (-not $env:CHEZMOI_SOURCE)
{
    $script:CHEZMOI_SOURCE = "$HOME\.local\share\chezmoi"
} else
{
    $script:CHEZMOI_SOURCE = $env:CHEZMOI_SOURCE
}

# ============================================================================
# CHEZMOI VERIFICATION
# ============================================================================

# Check if chezmoi is installed
function Verify-ChezmoiInstalled
{
    $null = Get-Command chezmoi -ErrorAction SilentlyContinue
    return $?
}

# Get chezmoi version
function Get-ChezmoiVersion
{
    if (Verify-ChezmoiInstalled)
    {
        $version = & chezmoi --version 2>$null | Select-Object -First 1
        return $version
    }
    return $null
}

# Check if chezmoi is initialized
function Verify-ChezmoiInitialized
{
    return (Test-Path "$script:CHEZMOI_SOURCE\.git")
}

# Get current chezmoi branch
function Get-ChezmoiBranch
{
    if (Verify-ChezmoiInitialized)
    {
        Push-Location $script:CHEZMOI_SOURCE
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        Pop-Location
        return $branch
    }
    return $null
}

# Check if dotfiles are applied (basic check for PowerShell profile)
function Verify-DotfilesApplied
{
    if (-not (Test-Path $PROFILE))
    {
        return $false
    }

    $null = & chezmoi verify 2>&1
    return $?
}

# ============================================================================
# CHEZMOI INSTALLATION
# ============================================================================

# Install chezmoi
function Install-Chezmoi
{
    Log-Header "Installing chezmoi"

    if (Verify-ChezmoiInstalled)
    {
        Log-Success "chezmoi already installed ($(Get-ChezmoiVersion))"
        return $true
    }

    Log-Info "Installing chezmoi..."

    # Try Scoop first
    if (Get-Command scoop -ErrorAction SilentlyContinue)
    {
        & scoop install chezmoi 2>&1 | Out-Null

        if (Verify-ChezmoiInstalled)
        {
            Log-Success "chezmoi installed via Scoop ($(Get-ChezmoiVersion))"
            return $true
        }
    }

    # Try winget
    if (Get-Command winget -ErrorAction SilentlyContinue)
    {
        & winget install --id twpayne.chezmoi --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        if (Verify-ChezmoiInstalled)
        {
            Log-Success "chezmoi installed via winget ($(Get-ChezmoiVersion))"
            return $true
        }
    }

    # Fallback to official installer
    try
    {
        Log-Info "Using official installer..."
        Invoke-Expression (Invoke-WebRequest -Uri 'https://get.chezmoi.io/ps1' -UseBasicParsing).Content

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        if (Verify-ChezmoiInstalled)
        {
            Log-Success "chezmoi installed ($(Get-ChezmoiVersion))"
            return $true
        }
    } catch
    {
        Log-Error "chezmoi installation failed: $_"
    }

    Log-Error "chezmoi installation failed"
    return $false
}

# ============================================================================
# DOTFILES INITIALIZATION
# ============================================================================

# Initialize chezmoi with dotfiles repo
function Initialize-Chezmoi
{
    param(
        [string]$Branch = "",
        [string]$Repo = $script:DOTFILES_REPO
    )

    Log-Header "Initializing chezmoi"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $false
    }

    # Check if already initialized with correct branch
    if (Verify-ChezmoiInitialized)
    {
        $currentBranch = Get-ChezmoiBranch

        if ($Branch -and $currentBranch -ne $Branch)
        {
            Log-Info "Switching chezmoi to branch: $Branch"
            Push-Location $script:CHEZMOI_SOURCE
            & git fetch origin $Branch 2>&1 | Out-Null
            & git checkout $Branch 2>&1 | Out-Null
            Pop-Location

            # Verify branch switch
            $currentBranch = Get-ChezmoiBranch
            if ($currentBranch -eq $Branch)
            {
                Log-Success "Switched to branch: $Branch"
            } else
            {
                Log-Warning "Failed to switch to branch: $Branch (on: $currentBranch)"
            }
        } else
        {
            Log-Success "chezmoi already initialized (branch: $currentBranch)"
        }
        return $true
    }

    Log-Info "Initializing chezmoi with $Repo..."

    $initArgs = @("init")
    if ($Branch)
    {
        $initArgs += "--branch"
        $initArgs += $Branch
    }
    $initArgs += $Repo

    & chezmoi @initArgs 2>&1 | Out-Null

    # Verify initialization
    if (Verify-ChezmoiInitialized)
    {
        $currentBranch = Get-ChezmoiBranch
        Log-Success "chezmoi initialized (branch: $currentBranch)"
        return $true
    } else
    {
        Log-Error "chezmoi initialization failed"
        return $false
    }
}

# ============================================================================
# DOTFILES APPLICATION
# ============================================================================

# Apply dotfiles
function Apply-Dotfiles
{
    Log-Header "Applying Dotfiles"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $false
    }

    if (-not (Verify-ChezmoiInitialized))
    {
        Log-Error "chezmoi not initialized. Run Initialize-Chezmoi first."
        return $false
    }

    Log-Info "Applying dotfiles..."
    $output = & chezmoi apply --verbose 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0)
    {
        Log-Success "Dotfiles applied successfully"
        return $true
    } else
    {
        Log-Error "Dotfiles apply failed (exit code: $exitCode)"
        Write-Output $output
        return $false
    }
}

# Initialize and apply dotfiles in one step
function Initialize-AndApplyDotfiles
{
    param(
        [string]$Branch = "",
        [string]$Repo = $script:DOTFILES_REPO
    )

    Log-Header "Applying Dotfiles with chezmoi"

    if (-not (Verify-ChezmoiInstalled))
    {
        if (-not (Install-Chezmoi))
        {
            return $false
        }
    }

    # Check if already applied
    if (Verify-DotfilesApplied)
    {
        Log-Success "Dotfiles already applied"
        return $true
    }

    Log-Info "Initializing and applying dotfiles..."

    $initArgs = @("init", "--apply")
    if ($Branch)
    {
        $initArgs += "--branch"
        $initArgs += $Branch
    }
    $initArgs += $Repo

    & chezmoi @initArgs
    $exitCode = $LASTEXITCODE

    # Verify application
    if (Test-Path $PROFILE)
    {
        Log-Success "Dotfiles applied successfully"
        return $true
    } elseif ($exitCode -eq 0)
    {
        Log-Success "chezmoi init --apply completed"
        return $true
    } else
    {
        Log-Error "Dotfiles application failed"
        return $false
    }
}

# ============================================================================
# DOTFILES UPDATE
# ============================================================================

# Update dotfiles from remote
function Update-Dotfiles
{
    Log-Header "Updating Dotfiles"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $false
    }

    if (-not (Verify-ChezmoiInitialized))
    {
        Log-Error "chezmoi not initialized"
        return $false
    }

    Log-Info "Pulling latest changes..."
    $output = & chezmoi update --verbose 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0)
    {
        Log-Success "Dotfiles updated successfully"
        return $true
    } else
    {
        Log-Error "Dotfiles update failed (exit code: $exitCode)"
        Write-Output $output
        return $false
    }
}

# ============================================================================
# DOTFILES DIFF
# ============================================================================

# Show diff between source and destination
function Show-DotfilesDiff
{
    Log-Header "Dotfiles Diff"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $false
    }

    if (-not (Verify-ChezmoiInitialized))
    {
        Log-Error "chezmoi not initialized"
        return $false
    }

    & chezmoi diff
    return $true
}

# ============================================================================
# DOTFILES VERIFICATION
# ============================================================================

# Verify all managed files are in sync
function Test-Dotfiles
{
    Log-Header "Verifying Dotfiles"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $false
    }

    if (-not (Verify-ChezmoiInitialized))
    {
        Log-Error "chezmoi not initialized"
        return $false
    }

    Log-Info "Checking for differences..."

    $diffOutput = & chezmoi diff 2>&1

    if (-not $diffOutput)
    {
        Log-Success "All dotfiles are in sync"
        return $true
    } else
    {
        Log-Warning "Dotfiles have differences:"
        Write-Output $diffOutput
        return $false
    }
}

# ============================================================================
# MANAGED FILES
# ============================================================================

# List managed files
function Get-ManagedFiles
{
    Log-Header "Managed Dotfiles"

    if (-not (Verify-ChezmoiInstalled))
    {
        Log-Error "chezmoi not installed"
        return $null
    }

    if (-not (Verify-ChezmoiInitialized))
    {
        Log-Error "chezmoi not initialized"
        return $null
    }

    return & chezmoi managed
}

# ============================================================================
# STATUS
# ============================================================================

# Show chezmoi status
function Get-ChezmoiStatus
{
    Log-Header "Chezmoi Status"

    if (Verify-ChezmoiInstalled)
    {
        Log-Success "chezmoi installed: $(Get-ChezmoiVersion)"
    } else
    {
        Log-Error "chezmoi not installed"
        return
    }

    if (Verify-ChezmoiInitialized)
    {
        $branch = Get-ChezmoiBranch
        Log-Success "chezmoi initialized (branch: $branch)"
        Log-Info "Source: $script:CHEZMOI_SOURCE"
    } else
    {
        Log-Warning "chezmoi not initialized"
        return
    }

    # Count managed files
    $managed = & chezmoi managed 2>$null
    $managedCount = ($managed | Measure-Object).Count
    Log-Info "Managed files: $managedCount"

    # Check for differences
    $diffOutput = & chezmoi diff 2>$null
    $diffCount = ($diffOutput | Select-String "^diff" | Measure-Object).Count

    if ($diffCount -eq 0)
    {
        Log-Success "All files in sync"
    } else
    {
        Log-Warning "$diffCount files have differences"
    }
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full dotfiles setup
function Setup-Dotfiles
{
    param(
        [string]$Branch = "",
        [string]$Repo = ""
    )

    # Use global variables if not explicitly provided
    if (-not $Branch -and $global:DOTFILES_BRANCH)
    {
        $Branch = $global:DOTFILES_BRANCH
    }
    if (-not $Repo)
    {
        if ($global:DOTFILES_REPO)
        {
            $Repo = $global:DOTFILES_REPO
        } else
        {
            $Repo = $script:DOTFILES_REPO
        }
    }

    $errors = 0

    if (-not (Install-Chezmoi))
    { $errors++
    }
    if (-not (Initialize-AndApplyDotfiles -Branch $Branch -Repo $Repo))
    { $errors++
    }

    if ($errors -gt 0)
    {
        Log-Warning "Dotfiles setup completed with $errors issues"
        return $false
    }

    Log-Success "Dotfiles setup complete"
    return $true
}

# ============================================================================
# EXPORTS
# ============================================================================

Export-ModuleMember -Function @(
    'Verify-ChezmoiInstalled',
    'Get-ChezmoiVersion',
    'Verify-ChezmoiInitialized',
    'Get-ChezmoiBranch',
    'Verify-DotfilesApplied',
    'Install-Chezmoi',
    'Initialize-Chezmoi',
    'Apply-Dotfiles',
    'Initialize-AndApplyDotfiles',
    'Update-Dotfiles',
    'Show-DotfilesDiff',
    'Test-Dotfiles',
    'Get-ManagedFiles',
    'Get-ChezmoiStatus',
    'Setup-Dotfiles'
) -ErrorAction SilentlyContinue
