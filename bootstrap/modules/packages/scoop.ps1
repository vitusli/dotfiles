# ============================================================================
# SCOOP PACKAGE MODULE
# Handles Scoop installation and packages for Windows
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Header -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}
if (-not (Get-Command Load-Packages -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "config.ps1")
}

# ============================================================================
# SCOOP BUCKETS
# ============================================================================

$SCOOP_BUCKETS = @(
    "main"
    "extras"
    "versions"
    "nerd-fonts"
)

# ============================================================================
# SCOOP VERIFICATION
# ============================================================================

# Check if Scoop is installed
function Verify-ScoopInstalled
{
    $null = Get-Command scoop -ErrorAction SilentlyContinue
    return $?
}

# Check if a Scoop package is installed
function Verify-ScoopPackageInstalled
{
    param([string]$PackageName)

    $result = @(scoop list $PackageName 2>$null | Where-Object { $_.Name -eq $PackageName })
    return $result.Count -gt 0
}

# Get installed package version
function Get-ScoopPackageVersion
{
    param([string]$PackageName)

    $result = scoop list $PackageName 2>$null | Where-Object { $_.Name -eq $PackageName }
    if ($result)
    {
        return $result.Version
    }
    return $null
}

# Check if a bucket is added
function Verify-ScoopBucketAdded
{
    param([string]$BucketName)

    $buckets = scoop bucket list 2>$null
    return $buckets -match $BucketName
}

# ============================================================================
# SCOOP INSTALLATION
# ============================================================================

# Install Scoop
function Install-Scoop
{
    Log-Header "Setting up Scoop"

    if (Verify-ScoopInstalled)
    {
        Log-Success "Scoop already installed"
        return $true
    }

    Log-Info "Installing Scoop..."

    # Set execution policy for current user
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force | Out-Null

    # Install Scoop
    try
    {
        Invoke-Expression "& {$(Invoke-RestMethod get.scoop.sh)} -RunAsAdmin"
    } catch
    {
        Log-Error "Scoop installation command failed: $_"
    }

    # Verify installation
    if (Verify-ScoopInstalled)
    {
        Log-Success "Scoop installed"
        return $true
    } else
    {
        Log-Error "Scoop installation failed - scoop command not found"
        return $false
    }
}

# ============================================================================
# BUCKET MANAGEMENT
# ============================================================================

# Add Scoop buckets
function Add-ScoopBuckets
{
    Log-Header "Adding Scoop Buckets"

    if (-not (Verify-ScoopInstalled))
    {
        Log-Error "Scoop not installed"
        return $false
    }

    $failed = @()

    foreach ($bucket in $SCOOP_BUCKETS)
    {
        if (Verify-ScoopBucketAdded $bucket)
        {
            Log-Success "Bucket '$bucket' already added"
        } else
        {
            Log-Info "Adding bucket: $bucket"
            scoop bucket add $bucket 2>&1 | Out-Null

            # Verify bucket was added
            if (Verify-ScoopBucketAdded $bucket)
            {
                Log-Success "Bucket '$bucket' added"
            } else
            {
                Log-Error "Failed to add bucket '$bucket'"
                $failed += $bucket
            }
        }
    }

    if ($failed.Count -gt 0)
    {
        Log-Warning "Failed to add buckets: $($failed -join ', ')"
        return $false
    }

    return $true
}

# ============================================================================
# PACKAGE INSTALLATION
# ============================================================================

# Install Scoop packages from config
function Install-ScoopPackages
{
    Log-Header "Installing Scoop Packages"

    if (-not (Verify-ScoopInstalled))
    {
        Log-Error "Scoop not installed"
        return $false
    }

    Log-Info "Loading packages from config..."
    $cliPackages = Load-Packages "cli.txt" "windows"
    $guiPackages = Load-Packages "gui.txt" "windows"

    $allPackages = @($cliPackages) + @($guiPackages) | Where-Object { $_ }

    $toInstall = @()
    $alreadyInstalled = 0
    $failed = @()

    foreach ($package in $allPackages)
    {
        if (-not $package)
        { continue 
        }

        if (Verify-ScoopPackageInstalled $package)
        {
            $version = Get-ScoopPackageVersion $package
            Log-Success "$package ($version)"
            $alreadyInstalled++
        } else
        {
            $toInstall += $package
        }
    }

    if ($toInstall.Count -eq 0)
    {
        Log-Info "All $alreadyInstalled packages already installed"
        return $true
    }

    Log-Info "Installing $($toInstall.Count) packages..."

    foreach ($package in $toInstall)
    {
        Log-Info "Installing $package..."
        scoop install $package 2>&1 | Out-Null

        # Verify installation
        if (Verify-ScoopPackageInstalled $package)
        {
            $version = Get-ScoopPackageVersion $package
            Log-Success "$package installed ($version)"
        } else
        {
            Log-Error "$package installation failed"
            $failed += $package
        }
    }

    # Summary
    $installed = $toInstall.Count - $failed.Count
    if ($failed.Count -gt 0)
    {
        Log-Warning "Installed $installed/$($toInstall.Count) packages. Failed: $($failed -join ', ')"
        return $false
    } else
    {
        Log-Success "All packages installed successfully"
        return $true
    }
}

# ============================================================================
# PACKAGE REMOVAL
# ============================================================================

# Remove a specific package
function Remove-ScoopPackage
{
    param([string]$PackageName)

    if (-not (Verify-ScoopPackageInstalled $PackageName))
    {
        Log-Info "$PackageName not installed"
        return $true
    }

    Log-Info "Removing $PackageName..."
    scoop uninstall $PackageName 2>&1 | Out-Null

    # Verify removal
    if (-not (Verify-ScoopPackageInstalled $PackageName))
    {
        Log-Success "$PackageName removed"
        return $true
    } else
    {
        Log-Error "$PackageName removal failed"
        return $false
    }
}

# ============================================================================
# CLEANUP
# ============================================================================

# Clean up Scoop cache and old versions
function Cleanup-Scoop
{
    Log-Header "Cleaning up Scoop"

    if (-not (Verify-ScoopInstalled))
    {
        Log-Error "Scoop not installed"
        return $false
    }

    Log-Info "Removing old versions..."
    scoop cleanup * 2>&1 | Out-Null

    Log-Info "Clearing cache..."
    scoop cache rm * 2>&1 | Out-Null

    Log-Success "Scoop cleanup complete"
    return $true
}

# ============================================================================
# UPDATE
# ============================================================================

# Update Scoop and all packages
function Update-Scoop
{
    Log-Header "Updating Scoop"

    if (-not (Verify-ScoopInstalled))
    {
        Log-Error "Scoop not installed"
        return $false
    }

    Log-Info "Updating Scoop..."
    scoop update 2>&1 | Out-Null

    Log-Info "Updating all packages..."
    $updateOutput = scoop update * 2>&1

    # Log the output
    Add-Content -Path $LOG_FILE -Value $updateOutput

    Log-Success "Scoop update complete"
    return $true
}

# ============================================================================
# STATUS
# ============================================================================

# Show status of all packages
function Get-ScoopStatus
{
    Log-Header "Scoop Package Status"

    if (-not (Verify-ScoopInstalled))
    {
        Log-Error "Scoop not installed"
        return
    }

    Log-Info "Checking for updates..."
    $status = scoop status 2>&1

    if ($status -match "Everything is ok")
    {
        Log-Success "All packages are up to date"
    } else
    {
        Log-Info "Packages with available updates:"
        Write-Output $status
    }
}

# ============================================================================
# EXPORT
# ============================================================================

Export-ModuleMember -Function @(
    'Verify-ScoopInstalled',
    'Verify-ScoopPackageInstalled',
    'Verify-ScoopBucketAdded',
    'Get-ScoopPackageVersion',
    'Install-Scoop',
    'Add-ScoopBuckets',
    'Install-ScoopPackages',
    'Remove-ScoopPackage',
    'Cleanup-Scoop',
    'Update-Scoop',
    'Get-ScoopStatus'
) -Variable @('SCOOP_BUCKETS')
