# ============================================================================
# WINDOWS FEATURES MODULE
# Handles Windows optional features management
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Info -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}

# ============================================================================
# CONFIGURATION
# ============================================================================

# Features to disable by default
$script:FEATURES_TO_DISABLE = @(
    "XPS-Viewer"
    "WindowsMediaPlayer"
    "Printing-XPSServices-Features"
    "WorkFolders-Client"
)

# ============================================================================
# VERIFICATION
# ============================================================================

function Verify-FeatureEnabled
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$FeatureName
    )

    try
    {
        $feature = Get-WindowsOptionalFeature -FeatureName $FeatureName -Online -ErrorAction SilentlyContinue
        return ($feature -and $feature.State -eq "Enabled")
    } catch
    {
        return $false
    }
}

function Verify-FeatureDisabled
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$FeatureName
    )

    try
    {
        $feature = Get-WindowsOptionalFeature -FeatureName $FeatureName -Online -ErrorAction SilentlyContinue
        return ($feature -and $feature.State -ne "Enabled")
    } catch
    {
        return $true
    }
}

function Verify-FeatureExists
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$FeatureName
    )

    try
    {
        $feature = Get-WindowsOptionalFeature -FeatureName $FeatureName -Online -ErrorAction SilentlyContinue
        return ($null -ne $feature)
    } catch
    {
        return $false
    }
}

# ============================================================================
# FEATURE MANAGEMENT
# ============================================================================

function Enable-WindowsFeature
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$FeatureName,

        [switch]$NoRestart
    )

    if (-not (Verify-FeatureExists -FeatureName $FeatureName))
    {
        Log-Warning "Feature not found: $FeatureName"
        return $false
    }

    if (Verify-FeatureEnabled -FeatureName $FeatureName)
    {
        Log-Success "$FeatureName (already enabled)"
        return $true
    }

    try
    {
        Log-Info "Enabling $FeatureName..."

        $params = @{
            FeatureName = $FeatureName
            Online = $true
            NoRestart = $NoRestart
            ErrorAction = "Stop"
        }

        Enable-WindowsOptionalFeature @params | Out-Null

        if (Verify-FeatureEnabled -FeatureName $FeatureName)
        {
            Log-Success "$FeatureName enabled"
            return $true
        } else
        {
            Log-Warning "$FeatureName may require restart to complete"
            return $true
        }
    } catch
    {
        Log-Error "Failed to enable $FeatureName: $_"
        return $false
    }
}

function Disable-WindowsFeature
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$FeatureName,

        [switch]$NoRestart
    )

    if (-not (Verify-FeatureExists -FeatureName $FeatureName))
    {
        Log-Info "Feature not found (skipping): $FeatureName"
        return $true
    }

    if (Verify-FeatureDisabled -FeatureName $FeatureName)
    {
        Log-Success "$FeatureName (already disabled)"
        return $true
    }

    try
    {
        Log-Info "Disabling $FeatureName..."

        $params = @{
            FeatureName = $FeatureName
            Online = $true
            NoRestart = $NoRestart
            ErrorAction = "Stop"
        }

        Disable-WindowsOptionalFeature @params | Out-Null

        if (Verify-FeatureDisabled -FeatureName $FeatureName)
        {
            Log-Success "$FeatureName disabled"
            return $true
        } else
        {
            Log-Warning "$FeatureName may require restart to complete"
            return $true
        }
    } catch
    {
        Log-Error "Failed to disable $FeatureName: $_"
        return $false
    }
}

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

function Disable-WindowsFeatures
{
    param(
        [string[]]$Features = $script:FEATURES_TO_DISABLE
    )

    Log-Header "Disabling Windows Features"

    $errors = 0

    foreach ($feature in $Features)
    {
        if (-not (Disable-WindowsFeature -FeatureName $feature -NoRestart))
        {
            $errors++
        }
    }

    if ($errors -gt 0)
    {
        Log-Warning "Disabled features with $errors issues"
        return $false
    }

    Log-Success "All features disabled"
    return $true
}

function Get-WindowsFeaturesStatus
{
    Log-Header "Windows Features Status"

    Log-Info "Features to disable:"
    foreach ($feature in $script:FEATURES_TO_DISABLE)
    {
        if (-not (Verify-FeatureExists -FeatureName $feature))
        {
            Log-Info "  $feature (not available)"
        } elseif (Verify-FeatureDisabled -FeatureName $feature)
        {
            Log-Success "  $feature (disabled)"
        } else
        {
            Log-Warning "  $feature (enabled)"
        }
    }
}

function Setup-WindowsFeatures
{
    Disable-WindowsFeatures
}
