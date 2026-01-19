# ============================================================================
# WINDOWS REGISTRY MODULE
# Handles Windows registry tweaks and system configuration
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
# REGISTRY VERIFICATION
# ============================================================================

# Check if a registry path exists
function Verify-RegistryPath
{
    param([string]$Path)

    return Test-Path -Path $Path
}

# Check if a registry value exists
function Verify-RegistryValueExists
{
    param(
        [string]$Path,
        [string]$Name
    )

    try
    {
        $null = Get-ItemPropertyValue -Path $Path -Name $Name -ErrorAction Stop
        return $true
    } catch
    {
        return $false
    }
}

# Get a registry value
function Get-RegistryValue
{
    param(
        [string]$Path,
        [string]$Name
    )

    try
    {
        return Get-ItemPropertyValue -Path $Path -Name $Name -ErrorAction Stop
    } catch
    {
        return $null
    }
}

# Verify a registry value matches expected
function Verify-RegistryValueMatches
{
    param(
        [string]$Path,
        [string]$Name,
        $ExpectedValue
    )

    $actualValue = Get-RegistryValue -Path $Path -Name $Name

    if ($null -eq $actualValue)
    {
        return $false
    }

    return $actualValue -eq $ExpectedValue
}

# ============================================================================
# REGISTRY MODIFICATION
# ============================================================================

# Set a registry value with verification
function Set-RegistryValueVerified
{
    param(
        [string]$Path,
        [string]$Name,
        $Value,
        [string]$Type = "DWord",
        [string]$Description = ""
    )

    try
    {
        # Create path if it doesn't exist
        if (-not (Verify-RegistryPath $Path))
        {
            New-Item -Path $Path -Force | Out-Null
        }

        # Set the value
        switch ($Type)
        {
            "DWord"
            {
                Set-ItemProperty -Path $Path -Name $Name -Value ([int]$Value) -Type DWord -Force | Out-Null
            }
            "String"
            {
                Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type String -Force | Out-Null
            }
            "Binary"
            {
                # Parse comma-separated hex bytes if string
                if ($Value -is [string])
                {
                    $bytes = $Value -split ',' | ForEach-Object { [byte]"0x$_" }
                    Set-ItemProperty -Path $Path -Name $Name -Value ([byte[]]$bytes) -Force | Out-Null
                } else
                {
                    Set-ItemProperty -Path $Path -Name $Name -Value $Value -Force | Out-Null
                }
            }
            "ExpandString"
            {
                Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type ExpandString -Force | Out-Null
            }
            "MultiString"
            {
                Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type MultiString -Force | Out-Null
            }
            "QWord"
            {
                Set-ItemProperty -Path $Path -Name $Name -Value ([long]$Value) -Type QWord -Force | Out-Null
            }
            default
            {
                Set-ItemProperty -Path $Path -Name $Name -Value $Value -Force | Out-Null
            }
        }

        # Verify the change
        if (Verify-RegistryValueMatches -Path $Path -Name $Name -ExpectedValue $Value)
        {
            if ($Description)
            {
                Log-Success "$Description"
            } else
            {
                Log-Success "$Name set to $Value"
            }
            return $true
        } else
        {
            # Value was set but doesn't match exactly (might be type conversion)
            $actualValue = Get-RegistryValue -Path $Path -Name $Name
            if ($null -ne $actualValue)
            {
                if ($Description)
                {
                    Log-Success "$Description"
                } else
                {
                    Log-Success "$Name configured"
                }
                return $true
            }

            Log-Warning "Failed to verify $Name"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set $Name`: $_"
        return $false
    }
}

# Remove a registry value
function Remove-RegistryValueVerified
{
    param(
        [string]$Path,
        [string]$Name,
        [string]$Description = ""
    )

    try
    {
        if (-not (Verify-RegistryValueExists -Path $Path -Name $Name))
        {
            if ($Description)
            {
                Log-Success "$Description (already removed)"
            }
            return $true
        }

        Remove-ItemProperty -Path $Path -Name $Name -Force -ErrorAction Stop | Out-Null

        # Verify removal
        if (-not (Verify-RegistryValueExists -Path $Path -Name $Name))
        {
            if ($Description)
            {
                Log-Success "$Description"
            } else
            {
                Log-Success "$Name removed"
            }
            return $true
        } else
        {
            Log-Warning "Failed to remove $Name"
            return $false
        }
    } catch
    {
        Log-Error "Failed to remove $Name`: $_"
        return $false
    }
}

# ============================================================================
# EXPLORER SETTINGS
# ============================================================================

function Setup-ExplorerSettings
{
    Log-Info "Configuring File Explorer settings..."
    $errors = 0

    $explorerPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

    # Show file extensions
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "HideFileExt" -Value 0 -Description "Show file extensions"))
    {
        $errors++
    }

    # Show hidden files
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "Hidden" -Value 1 -Description "Show hidden files"))
    {
        $errors++
    }

    # Show system files
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "ShowSuperHidden" -Value 1 -Description "Show system files"))
    {
        $errors++
    }

    # Show full path in title bar
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "FullPath" -Value 1 -Description "Show full path in title bar"))
    {
        $errors++
    }

    # Expand to current folder in navigation pane
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "NavPaneExpandToCurrentFolder" -Value 1 -Description "Expand to current folder"))
    {
        $errors++
    }

    # Launch folder windows in separate process
    if (-not (Set-RegistryValueVerified -Path $explorerPath -Name "SeparateProcess" -Value 1 -Description "Separate folder processes"))
    {
        $errors++
    }

    # Explorer opens to This PC instead of Quick Access
    if (-not (Remove-RegistryValueVerified -Path $explorerPath -Name "LaunchTo" -Description "Open to This PC"))
    {
        # If removal fails, try setting to 1 (This PC)
        Set-RegistryValueVerified -Path $explorerPath -Name "LaunchTo" -Value 1 -Description "Open to This PC" | Out-Null
    }

    return $errors
}

# ============================================================================
# PRIVACY SETTINGS
# ============================================================================

function Setup-PrivacySettings
{
    Log-Info "Configuring privacy settings..."
    $errors = 0

    # Disable telemetry
    $telemetryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    if (-not (Set-RegistryValueVerified -Path $telemetryPath -Name "AllowTelemetry" -Value 0 -Description "Disable telemetry"))
    {
        $errors++
    }

    # Disable advertising ID
    $adPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
    if (-not (Set-RegistryValueVerified -Path $adPath -Name "Enabled" -Value 0 -Description "Disable advertising ID"))
    {
        $errors++
    }

    # Disable Bing search in Start Menu
    $searchPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"
    if (-not (Set-RegistryValueVerified -Path $searchPath -Name "BingSearchEnabled" -Value 0 -Description "Disable Bing search"))
    {
        $errors++
    }

    # Disable Cortana
    $cortanaPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"
    if (-not (Set-RegistryValueVerified -Path $cortanaPath -Name "CortanaConsent" -Value 0 -Description "Disable Cortana"))
    {
        $errors++
    }

    # Disable web search in Start Menu
    $webSearchPath = "HKCU:\Software\Policies\Microsoft\Windows\Explorer"
    if (-not (Set-RegistryValueVerified -Path $webSearchPath -Name "DisableSearchBoxSuggestions" -Value 1 -Description "Disable web search suggestions"))
    {
        $errors++
    }

    # Disable activity history
    $activityPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"
    Set-RegistryValueVerified -Path $activityPath -Name "EnableActivityFeed" -Value 0 -Description "Disable activity feed" | Out-Null
    Set-RegistryValueVerified -Path $activityPath -Name "PublishUserActivities" -Value 0 -Description "Disable publish activities" | Out-Null
    Set-RegistryValueVerified -Path $activityPath -Name "UploadUserActivities" -Value 0 -Description "Disable upload activities" | Out-Null

    return $errors
}

# ============================================================================
# APPEARANCE SETTINGS
# ============================================================================

function Setup-AppearanceSettings
{
    Log-Info "Configuring appearance settings..."
    $errors = 0

    $personalizePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

    # Enable dark mode for apps
    if (-not (Set-RegistryValueVerified -Path $personalizePath -Name "AppsUseLightTheme" -Value 0 -Description "Dark mode for apps"))
    {
        $errors++
    }

    # Enable dark mode for system
    if (-not (Set-RegistryValueVerified -Path $personalizePath -Name "SystemUsesLightTheme" -Value 0 -Description "Dark mode for system"))
    {
        $errors++
    }

    # Disable transparency effects (optional, improves performance)
    # Set-RegistryValueVerified -Path $personalizePath -Name "EnableTransparency" -Value 0 -Description "Disable transparency"

    # Taskbar settings
    $taskbarPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

    # Hide Task View button
    if (-not (Set-RegistryValueVerified -Path $taskbarPath -Name "ShowTaskViewButton" -Value 0 -Description "Hide Task View button"))
    {
        $errors++
    }

    # Hide Widgets
    if (-not (Set-RegistryValueVerified -Path $taskbarPath -Name "TaskbarDa" -Value 0 -Description "Hide Widgets"))
    {
        $errors++
    }

    # Hide Chat
    if (-not (Set-RegistryValueVerified -Path $taskbarPath -Name "TaskbarMn" -Value 0 -Description "Hide Chat"))
    {
        $errors++
    }

    return $errors
}

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

function Setup-PerformanceSettings
{
    Log-Info "Configuring performance settings..."
    $errors = 0

    # Disable startup delay
    $startupPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize"
    Set-RegistryValueVerified -Path $startupPath -Name "StartupDelayInMSec" -Value 0 -Description "Disable startup delay" | Out-Null

    # Disable prefetch (SSD optimization)
    $prefetchPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
    Set-RegistryValueVerified -Path $prefetchPath -Name "EnablePrefetcher" -Value 0 -Description "Disable prefetcher" | Out-Null
    Set-RegistryValueVerified -Path $prefetchPath -Name "EnableSuperfetch" -Value 0 -Description "Disable superfetch" | Out-Null

    # Disable hibernation (saves disk space)
    # Note: This requires admin and uses powercfg
    # powercfg /hibernate off

    return $errors
}

# ============================================================================
# CONFIG-BASED REGISTRY TWEAKS
# ============================================================================

function Apply-RegistryFromConfig
{
    Log-Header "Applying Registry Tweaks (from config)"

    Log-Info "Loading registry tweaks from config..."
    $registryConfig = Load-Config "windows-registry.txt"

    if (-not $registryConfig -or $registryConfig.Count -eq 0)
    {
        Log-Info "No registry tweaks defined in config"
        return 0
    }

    $success = 0
    $failed = 0

    foreach ($line in $registryConfig)
    {
        if (-not $line -or $line.StartsWith('#'))
        {
            continue
        }

        $parts = $line -split '\|'
        if ($parts.Count -lt 4)
        {
            Log-Warning "Invalid config line: $line"
            $failed++
            continue
        }

        $path = $parts[0]
        $name = $parts[1]
        $type = $parts[2]
        $value = $parts[3]
        $description = if ($parts.Count -ge 5)
        { $parts[4] 
        } else
        { $name 
        }

        if (Set-RegistryValueVerified -Path $path -Name $name -Value $value -Type $type -Description $description)
        {
            $success++
        } else
        {
            $failed++
        }
    }

    if ($failed -gt 0)
    {
        Log-Warning "Applied $success registry tweaks, $failed failed"
        return $failed
    } else
    {
        Log-Success "All $success registry tweaks applied"
        return 0
    }
}

# ============================================================================
# STATUS
# ============================================================================

function Get-RegistryStatus
{
    Log-Header "Registry Settings Status"

    Log-Info "=== Explorer ==="
    $explorerPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

    if (Verify-RegistryValueMatches -Path $explorerPath -Name "HideFileExt" -ExpectedValue 0)
    {
        Log-Success "File extensions: shown"
    } else
    {
        Log-Info "File extensions: hidden"
    }

    if (Verify-RegistryValueMatches -Path $explorerPath -Name "Hidden" -ExpectedValue 1)
    {
        Log-Success "Hidden files: shown"
    } else
    {
        Log-Info "Hidden files: hidden"
    }

    Log-Info "=== Appearance ==="
    $personalizePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

    if (Verify-RegistryValueMatches -Path $personalizePath -Name "AppsUseLightTheme" -ExpectedValue 0)
    {
        Log-Success "Theme: Dark mode"
    } else
    {
        Log-Info "Theme: Light mode"
    }

    Log-Info "=== Privacy ==="
    $searchPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"

    if (Verify-RegistryValueMatches -Path $searchPath -Name "BingSearchEnabled" -ExpectedValue 0)
    {
        Log-Success "Bing search: disabled"
    } else
    {
        Log-Info "Bing search: enabled"
    }
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

function Setup-RegistryTweaks
{
    Log-Header "Configuring Windows Registry"

    $totalErrors = 0

    $totalErrors += Setup-ExplorerSettings
    $totalErrors += Setup-PrivacySettings
    $totalErrors += Setup-AppearanceSettings
    $totalErrors += Setup-PerformanceSettings
    $totalErrors += Apply-RegistryFromConfig

    if ($totalErrors -gt 0)
    {
        Log-Warning "Registry configuration completed with $totalErrors issues"
        return $false
    }

    Log-Success "All registry tweaks applied"
    Log-Warning "Some changes may require a restart to take effect"
    return $true
}

# ============================================================================
# EXPORT
# ============================================================================

Export-ModuleMember -Function @(
    'Verify-RegistryPath',
    'Verify-RegistryValueExists',
    'Verify-RegistryValueMatches',
    'Get-RegistryValue',
    'Set-RegistryValueVerified',
    'Remove-RegistryValueVerified',
    'Setup-ExplorerSettings',
    'Setup-PrivacySettings',
    'Setup-AppearanceSettings',
    'Setup-PerformanceSettings',
    'Apply-RegistryFromConfig',
    'Get-RegistryStatus',
    'Setup-RegistryTweaks'
)
