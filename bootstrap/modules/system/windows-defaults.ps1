# ============================================================================
# WINDOWS DEFAULTS MODULE
# Handles Windows system defaults and settings
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

$script:ExplorerAdvancedPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
$script:PersonalizePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
$script:SearchPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"
$script:DesktopPath = "HKCU:\Control Panel\Desktop"

# ============================================================================
# VERIFICATION
# ============================================================================

function Verify-FileExtensionsVisible
{
    try
    {
        $value = Get-ItemPropertyValue -Path $script:ExplorerAdvancedPath -Name "HideFileExt" -ErrorAction SilentlyContinue
        return ($value -eq 0)
    } catch
    {
        return $false
    }
}

function Verify-HiddenFilesVisible
{
    try
    {
        $value = Get-ItemPropertyValue -Path $script:ExplorerAdvancedPath -Name "Hidden" -ErrorAction SilentlyContinue
        return ($value -eq 1)
    } catch
    {
        return $false
    }
}

function Verify-SystemFilesVisible
{
    try
    {
        $value = Get-ItemPropertyValue -Path $script:ExplorerAdvancedPath -Name "ShowSuperHidden" -ErrorAction SilentlyContinue
        return ($value -eq 1)
    } catch
    {
        return $false
    }
}

function Verify-DarkModeEnabled
{
    try
    {
        $appsTheme = Get-ItemPropertyValue -Path $script:PersonalizePath -Name "AppsUseLightTheme" -ErrorAction SilentlyContinue
        $systemTheme = Get-ItemPropertyValue -Path $script:PersonalizePath -Name "SystemUsesLightTheme" -ErrorAction SilentlyContinue
        return ($appsTheme -eq 0 -and $systemTheme -eq 0)
    } catch
    {
        return $false
    }
}

function Verify-BingSearchDisabled
{
    try
    {
        $value = Get-ItemPropertyValue -Path $script:SearchPath -Name "BingSearchEnabled" -ErrorAction SilentlyContinue
        return ($value -eq 0)
    } catch
    {
        return $false
    }
}

# ============================================================================
# EXPLORER SETTINGS
# ============================================================================

function Set-FileExtensionsVisible
{
    param([bool]$Visible = $true)

    try
    {
        $value = if ($Visible)
        { 0 
        } else
        { 1 
        }
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "HideFileExt" -Value $value -Type DWord -Force | Out-Null

        if (Verify-FileExtensionsVisible -eq $Visible)
        {
            $status = if ($Visible)
            { "visible" 
            } else
            { "hidden" 
            }
            Log-Success "File extensions: $status"
            return $true
        } else
        {
            Log-Warning "Failed to set file extensions visibility"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set file extensions visibility: $_"
        return $false
    }
}

function Set-HiddenFilesVisible
{
    param([bool]$Visible = $true)

    try
    {
        $value = if ($Visible)
        { 1 
        } else
        { 2 
        }
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "Hidden" -Value $value -Type DWord -Force | Out-Null

        if (Verify-HiddenFilesVisible -eq $Visible)
        {
            $status = if ($Visible)
            { "visible" 
            } else
            { "hidden" 
            }
            Log-Success "Hidden files: $status"
            return $true
        } else
        {
            Log-Warning "Failed to set hidden files visibility"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set hidden files visibility: $_"
        return $false
    }
}

function Set-SystemFilesVisible
{
    param([bool]$Visible = $true)

    try
    {
        $value = if ($Visible)
        { 1 
        } else
        { 0 
        }
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "ShowSuperHidden" -Value $value -Type DWord -Force | Out-Null

        if (Verify-SystemFilesVisible -eq $Visible)
        {
            $status = if ($Visible)
            { "visible" 
            } else
            { "hidden" 
            }
            Log-Success "System files: $status"
            return $true
        } else
        {
            Log-Warning "Failed to set system files visibility"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set system files visibility: $_"
        return $false
    }
}

function Set-FullPathInTitleBar
{
    param([bool]$Enabled = $true)

    try
    {
        $value = if ($Enabled)
        { 1 
        } else
        { 0 
        }
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "FullPath" -Value $value -Type DWord -Force | Out-Null
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "FullPathAddress" -Value $value -Type DWord -Force | Out-Null

        $status = if ($Enabled)
        { "enabled" 
        } else
        { "disabled" 
        }
        Log-Success "Full path in title bar: $status"
        return $true
    } catch
    {
        Log-Error "Failed to set full path in title bar: $_"
        return $false
    }
}

# ============================================================================
# THEME SETTINGS
# ============================================================================

function Set-DarkMode
{
    param([bool]$Enabled = $true)

    try
    {
        $value = if ($Enabled)
        { 0 
        } else
        { 1 
        }

        # Ensure path exists
        if (-not (Test-Path $script:PersonalizePath))
        {
            New-Item -Path $script:PersonalizePath -Force | Out-Null
        }

        Set-ItemProperty -Path $script:PersonalizePath -Name "AppsUseLightTheme" -Value $value -Type DWord -Force | Out-Null
        Set-ItemProperty -Path $script:PersonalizePath -Name "SystemUsesLightTheme" -Value $value -Type DWord -Force | Out-Null

        if (Verify-DarkModeEnabled -eq $Enabled)
        {
            $status = if ($Enabled)
            { "enabled" 
            } else
            { "disabled" 
            }
            Log-Success "Dark mode: $status"
            return $true
        } else
        {
            Log-Warning "Failed to set dark mode"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set dark mode: $_"
        return $false
    }
}

# ============================================================================
# SEARCH SETTINGS
# ============================================================================

function Set-BingSearchDisabled
{
    param([bool]$Disabled = $true)

    try
    {
        $value = if ($Disabled)
        { 0 
        } else
        { 1 
        }

        # Ensure path exists
        if (-not (Test-Path $script:SearchPath))
        {
            New-Item -Path $script:SearchPath -Force | Out-Null
        }

        Set-ItemProperty -Path $script:SearchPath -Name "BingSearchEnabled" -Value $value -Type DWord -Force | Out-Null

        if (Verify-BingSearchDisabled -eq $Disabled)
        {
            $status = if ($Disabled)
            { "disabled" 
            } else
            { "enabled" 
            }
            Log-Success "Bing search in Start menu: $status"
            return $true
        } else
        {
            Log-Warning "Failed to set Bing search status"
            return $false
        }
    } catch
    {
        Log-Error "Failed to set Bing search status: $_"
        return $false
    }
}

function Set-CortanaDisabled
{
    param([bool]$Disabled = $true)

    try
    {
        $value = if ($Disabled)
        { 0 
        } else
        { 1 
        }

        # Ensure path exists
        if (-not (Test-Path $script:SearchPath))
        {
            New-Item -Path $script:SearchPath -Force | Out-Null
        }

        Set-ItemProperty -Path $script:SearchPath -Name "CortanaConsent" -Value $value -Type DWord -Force | Out-Null

        $status = if ($Disabled)
        { "disabled" 
        } else
        { "enabled" 
        }
        Log-Success "Cortana: $status"
        return $true
    } catch
    {
        Log-Error "Failed to set Cortana status: $_"
        return $false
    }
}

# ============================================================================
# TASKBAR SETTINGS
# ============================================================================

function Set-TaskbarSearch
{
    param(
        [ValidateSet("Hidden", "Icon", "Box")]
        [string]$Mode = "Icon"
    )

    try
    {
        $value = switch ($Mode)
        {
            "Hidden"
            { 0 
            }
            "Icon"
            { 1 
            }
            "Box"
            { 2 
            }
        }

        Set-ItemProperty -Path $script:SearchPath -Name "SearchboxTaskbarMode" -Value $value -Type DWord -Force | Out-Null
        Log-Success "Taskbar search: $Mode"
        return $true
    } catch
    {
        Log-Error "Failed to set taskbar search mode: $_"
        return $false
    }
}

function Set-TaskViewButtonHidden
{
    param([bool]$Hidden = $true)

    try
    {
        $value = if ($Hidden)
        { 0 
        } else
        { 1 
        }
        Set-ItemProperty -Path $script:ExplorerAdvancedPath -Name "ShowTaskViewButton" -Value $value -Type DWord -Force | Out-Null

        $status = if ($Hidden)
        { "hidden" 
        } else
        { "visible" 
        }
        Log-Success "Task View button: $status"
        return $true
    } catch
    {
        Log-Error "Failed to set Task View button visibility: $_"
        return $false
    }
}

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

function Apply-SystemDefaults
{
    Log-Header "Configuring System Defaults"

    $errors = 0

    # Explorer settings
    if (-not (Set-FileExtensionsVisible -Visible $true))
    { $errors++ 
    }
    if (-not (Set-HiddenFilesVisible -Visible $true))
    { $errors++ 
    }
    if (-not (Set-SystemFilesVisible -Visible $true))
    { $errors++ 
    }

    # Theme
    if (-not (Set-DarkMode -Enabled $true))
    { $errors++ 
    }

    # Search
    if (-not (Set-BingSearchDisabled -Disabled $true))
    { $errors++ 
    }

    if ($errors -gt 0)
    {
        Log-Warning "System defaults applied with $errors issues"
        return $false
    }

    Log-Success "System defaults applied"
    return $true
}

function Get-SystemDefaultsStatus
{
    Log-Header "System Defaults Status"

    # Explorer settings
    if (Verify-FileExtensionsVisible)
    {
        Log-Success "File extensions: visible"
    } else
    {
        Log-Warning "File extensions: hidden"
    }

    if (Verify-HiddenFilesVisible)
    {
        Log-Success "Hidden files: visible"
    } else
    {
        Log-Warning "Hidden files: hidden"
    }

    if (Verify-SystemFilesVisible)
    {
        Log-Success "System files: visible"
    } else
    {
        Log-Warning "System files: hidden"
    }

    # Theme
    if (Verify-DarkModeEnabled)
    {
        Log-Success "Dark mode: enabled"
    } else
    {
        Log-Info "Dark mode: disabled"
    }

    # Search
    if (Verify-BingSearchDisabled)
    {
        Log-Success "Bing search: disabled"
    } else
    {
        Log-Warning "Bing search: enabled"
    }
}

function Setup-WindowsDefaults
{
    Apply-SystemDefaults
}
