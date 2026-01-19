# ============================================================================
# WINDOWS BLOATWARE REMOVAL MODULE
# Handles removal of pre-installed Windows apps (AppX packages)
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Header -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}
if (-not (Get-Command Load-Config -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "config.ps1")
}

# ============================================================================
# APPX VERIFICATION
# ============================================================================

# Check if an AppX package is installed (for current user)
function Verify-AppxInstalled
{
    param([string]$PackageName)

    $packages = @(Get-AppxPackage -Name $PackageName -ErrorAction SilentlyContinue)
    return $packages.Count -gt 0
}

# Check if an AppX package is installed for all users
function Verify-AppxInstalledAllUsers
{
    param([string]$PackageName)

    $packages = @(Get-AppxPackage -Name $PackageName -AllUsers -ErrorAction SilentlyContinue)
    return $packages.Count -gt 0
}

# Check if an AppX package is provisioned (will reinstall for new users)
function Verify-AppxProvisioned
{
    param([string]$PackageName)

    $provisioned = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq $PackageName -or $_.PackageName -like "*$PackageName*" }
    return $null -ne $provisioned
}

# Get installed AppX packages matching a pattern
function Get-InstalledAppxPackages
{
    param([string]$Pattern = "*")

    Get-AppxPackage -Name $Pattern -AllUsers -ErrorAction SilentlyContinue
}

# ============================================================================
# APPX REMOVAL
# ============================================================================

# Remove an AppX package for all users with verification
function Remove-AppxVerified
{
    param(
        [string]$PackageName,
        [string]$Description = ""
    )

    $displayName = if ($Description)
    { $Description 
    } else
    { $PackageName 
    }

    # Check if installed
    if (-not (Verify-AppxInstalledAllUsers $PackageName))
    {
        Log-Success "$displayName (not installed)"
        return $true
    }

    try
    {
        Log-Info "Removing $displayName..."

        # Remove for all users
        Get-AppxPackage -Name $PackageName -AllUsers -ErrorAction SilentlyContinue |
            Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue

        # Verify removal
        if (-not (Verify-AppxInstalledAllUsers $PackageName))
        {
            Log-Success "$displayName removed"
            return $true
        } else
        {
            Log-Warning "Failed to remove $displayName"
            return $false
        }
    } catch
    {
        Log-Warning "Could not remove $displayName`: $_"
        return $false
    }
}

# Remove provisioned package (prevents reinstall for new users)
function Remove-AppxProvisionedVerified
{
    param(
        [string]$PackageName,
        [string]$Description = ""
    )

    $displayName = if ($Description)
    { $Description 
    } else
    { $PackageName 
    }

    # Check if provisioned
    if (-not (Verify-AppxProvisioned $PackageName))
    {
        return $true
    }

    try
    {
        $provisioned = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -eq $PackageName -or $_.PackageName -like "*$PackageName*" }

        if ($provisioned)
        {
            $provisioned | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Out-Null
            Log-Debug "Removed provisioned package: $displayName"
        }

        return $true
    } catch
    {
        Log-Debug "Could not remove provisioned $displayName`: $_"
        return $false
    }
}

# Remove an AppX package completely (installed + provisioned)
function Remove-AppxCompletely
{
    param(
        [string]$PackageName,
        [string]$Description = ""
    )

    $displayName = if ($Description)
    { $Description 
    } else
    { $PackageName 
    }

    # Remove installed package
    $removed = Remove-AppxVerified -PackageName $PackageName -Description $displayName

    # Remove provisioned package to prevent reinstall
    Remove-AppxProvisionedVerified -PackageName $PackageName -Description $displayName | Out-Null

    return $removed
}

# ============================================================================
# COMMON BLOATWARE LIST
# ============================================================================

# Common Windows bloatware apps
$BLOATWARE_APPS = @(
    @{ Name = "Microsoft.3DBuilder"; Description = "3D Builder" }
    @{ Name = "Microsoft.549981C3F5F10"; Description = "Cortana" }
    @{ Name = "Microsoft.Advertising.Xaml"; Description = "Advertising" }
    @{ Name = "Microsoft.BingFinance"; Description = "Bing Finance" }
    @{ Name = "Microsoft.BingNews"; Description = "Bing News" }
    @{ Name = "Microsoft.BingSports"; Description = "Bing Sports" }
    @{ Name = "Microsoft.BingWeather"; Description = "Bing Weather" }
    @{ Name = "Microsoft.GetHelp"; Description = "Get Help" }
    @{ Name = "Microsoft.Getstarted"; Description = "Tips" }
    @{ Name = "Microsoft.Messaging"; Description = "Messaging" }
    @{ Name = "Microsoft.Microsoft3DViewer"; Description = "3D Viewer" }
    @{ Name = "Microsoft.MicrosoftOfficeHub"; Description = "Office Hub" }
    @{ Name = "Microsoft.MicrosoftSolitaireCollection"; Description = "Solitaire" }
    @{ Name = "Microsoft.MixedReality.Portal"; Description = "Mixed Reality Portal" }
    @{ Name = "Microsoft.MSPaint"; Description = "Paint 3D" }
    @{ Name = "Microsoft.Office.OneNote"; Description = "OneNote" }
    @{ Name = "Microsoft.OneConnect"; Description = "Mobile Plans" }
    @{ Name = "Microsoft.People"; Description = "People" }
    @{ Name = "Microsoft.Print3D"; Description = "Print 3D" }
    @{ Name = "Microsoft.ScreenSketch"; Description = "Snip & Sketch" }
    @{ Name = "Microsoft.SkypeApp"; Description = "Skype" }
    @{ Name = "Microsoft.Wallet"; Description = "Wallet" }
    @{ Name = "Microsoft.WindowsAlarms"; Description = "Alarms & Clock" }
    @{ Name = "Microsoft.WindowsCommunicationsApps"; Description = "Mail & Calendar" }
    @{ Name = "Microsoft.WindowsFeedbackHub"; Description = "Feedback Hub" }
    @{ Name = "Microsoft.WindowsMaps"; Description = "Maps" }
    @{ Name = "Microsoft.WindowsSoundRecorder"; Description = "Voice Recorder" }
    @{ Name = "Microsoft.Xbox.TCUI"; Description = "Xbox TCUI" }
    @{ Name = "Microsoft.XboxApp"; Description = "Xbox App" }
    @{ Name = "Microsoft.XboxGameOverlay"; Description = "Xbox Game Bar" }
    @{ Name = "Microsoft.XboxGamingOverlay"; Description = "Xbox Gaming Overlay" }
    @{ Name = "Microsoft.XboxIdentityProvider"; Description = "Xbox Identity" }
    @{ Name = "Microsoft.XboxSpeechToTextOverlay"; Description = "Xbox Speech" }
    @{ Name = "Microsoft.YourPhone"; Description = "Your Phone" }
    @{ Name = "Microsoft.ZuneMusic"; Description = "Groove Music" }
    @{ Name = "Microsoft.ZuneVideo"; Description = "Movies & TV" }
    @{ Name = "MicrosoftCorporationII.QuickAssist"; Description = "Quick Assist" }
    @{ Name = "MicrosoftTeams"; Description = "Microsoft Teams" }
    @{ Name = "Clipchamp.Clipchamp"; Description = "Clipchamp" }
)

# Third-party bloatware commonly pre-installed
$THIRDPARTY_BLOATWARE = @(
    @{ Name = "*AdobePhotoshopExpress*"; Description = "Adobe Photoshop Express" }
    @{ Name = "*Amazon*"; Description = "Amazon Apps" }
    @{ Name = "*BubbleWitch*"; Description = "Bubble Witch" }
    @{ Name = "*CandyCrush*"; Description = "Candy Crush" }
    @{ Name = "*Disney*"; Description = "Disney Apps" }
    @{ Name = "*Dolby*"; Description = "Dolby" }
    @{ Name = "*Duolingo*"; Description = "Duolingo" }
    @{ Name = "*EclipseManager*"; Description = "Eclipse Manager" }
    @{ Name = "*Facebook*"; Description = "Facebook" }
    @{ Name = "*Flipboard*"; Description = "Flipboard" }
    @{ Name = "*HiddenCity*"; Description = "Hidden City" }
    @{ Name = "*HiddenCityMysteryofShadows*"; Description = "Hidden City Mystery" }
    @{ Name = "*Hulu*"; Description = "Hulu" }
    @{ Name = "*Instagram*"; Description = "Instagram" }
    @{ Name = "*king.com*"; Description = "King.com Games" }
    @{ Name = "*LinkedIn*"; Description = "LinkedIn" }
    @{ Name = "*MarchofEmpires*"; Description = "March of Empires" }
    @{ Name = "*McAfee*"; Description = "McAfee" }
    @{ Name = "*Netflix*"; Description = "Netflix" }
    @{ Name = "*Pandora*"; Description = "Pandora" }
    @{ Name = "*Plex*"; Description = "Plex" }
    @{ Name = "*Royal Revolt*"; Description = "Royal Revolt" }
    @{ Name = "*Shazam*"; Description = "Shazam" }
    @{ Name = "*Spotify*"; Description = "Spotify" }
    @{ Name = "*Sway*"; Description = "Sway" }
    @{ Name = "*Twitter*"; Description = "Twitter" }
    @{ Name = "*Wunderlist*"; Description = "Wunderlist" }
)

# ============================================================================
# BULK REMOVAL
# ============================================================================

# Remove all Microsoft bloatware
function Remove-MicrosoftBloatware
{
    Log-Header "Removing Microsoft Bloatware"

    $removed = 0
    $failed = 0

    foreach ($app in $BLOATWARE_APPS)
    {
        if (Remove-AppxCompletely -PackageName $app.Name -Description $app.Description)
        {
            $removed++
        } else
        {
            $failed++
        }
    }

    if ($failed -gt 0)
    {
        Log-Warning "Removed $removed apps, $failed could not be removed"
        return $false
    }

    Log-Success "Removed $removed Microsoft bloatware apps"
    return $true
}

# Remove third-party bloatware
function Remove-ThirdPartyBloatware
{
    Log-Header "Removing Third-Party Bloatware"

    $removed = 0
    $notFound = 0

    foreach ($app in $THIRDPARTY_BLOATWARE)
    {
        # Check if installed
        if (Verify-AppxInstalledAllUsers $app.Name)
        {
            if (Remove-AppxCompletely -PackageName $app.Name -Description $app.Description)
            {
                $removed++
            }
        } else
        {
            $notFound++
        }
    }

    Log-Info "Removed: $removed, Not installed: $notFound"
    return $true
}

# ============================================================================
# CONFIG-BASED REMOVAL
# ============================================================================

# Remove bloatware from config file
function Remove-BloatwareFromConfig
{
    Log-Header "Removing Bloatware (from config)"

    Log-Info "Loading bloatware list from config..."
    $bloatwareConfig = Load-Config "windows-bloatware.txt"

    if (-not $bloatwareConfig -or $bloatwareConfig.Count -eq 0)
    {
        Log-Info "No bloatware defined in config"
        return $true
    }

    $removed = 0
    $notFound = 0
    $failed = 0

    foreach ($app in $bloatwareConfig)
    {
        if (-not $app -or $app.StartsWith('#'))
        {
            continue
        }

        # Check if installed
        if (-not (Verify-AppxInstalledAllUsers $app))
        {
            $notFound++
            continue
        }

        if (Remove-AppxCompletely -PackageName $app -Description $app)
        {
            $removed++
        } else
        {
            $failed++
        }
    }

    Log-Info "Removed: $removed, Not installed: $notFound, Failed: $failed"

    if ($failed -gt 0)
    {
        return $false
    }

    return $true
}

# ============================================================================
# STATUS
# ============================================================================

# Show bloatware status
function Get-BloatwareStatus
{
    Log-Header "Bloatware Status"

    Log-Info "=== Microsoft Bloatware ==="
    $installed = 0
    $removed = 0

    foreach ($app in $BLOATWARE_APPS)
    {
        if (Verify-AppxInstalledAllUsers $app.Name)
        {
            Log-Warning "$($app.Description): Installed"
            $installed++
        } else
        {
            Log-Success "$($app.Description): Removed"
            $removed++
        }
    }

    Log-Info ""
    Log-Info "Installed: $installed, Removed: $removed"
}

# List all installed AppX packages
function Get-AllInstalledAppx
{
    Log-Header "All Installed AppX Packages"

    $packages = Get-AppxPackage -AllUsers | Sort-Object Name

    Log-Info "Total packages: $($packages.Count)"
    Log-Info ""

    foreach ($pkg in $packages)
    {
        Write-Output "$($pkg.Name)"
    }
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full bloatware removal
function Remove-Bloatware
{
    $errors = 0

    if (-not (Remove-BloatwareFromConfig))
    {
        $errors++
    }

    if ($errors -gt 0)
    {
        Log-Warning "Bloatware removal completed with issues"
        return $false
    }

    Log-Success "Bloatware removal complete"
    return $true
}

# ============================================================================
# EXPORT
# ============================================================================

Export-ModuleMember -Function @(
    'Verify-AppxInstalled',
    'Verify-AppxInstalledAllUsers',
    'Verify-AppxProvisioned',
    'Get-InstalledAppxPackages',
    'Remove-AppxVerified',
    'Remove-AppxProvisionedVerified',
    'Remove-AppxCompletely',
    'Remove-MicrosoftBloatware',
    'Remove-ThirdPartyBloatware',
    'Remove-BloatwareFromConfig',
    'Get-BloatwareStatus',
    'Get-AllInstalledAppx',
    'Remove-Bloatware'
) -Variable @('BLOATWARE_APPS', 'THIRDPARTY_BLOATWARE')
