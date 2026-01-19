# ============================================================================
# WINDOWS SERVICES MODULE
# Handles Windows service management (disable/enable services)
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
# SERVICE VERIFICATION
# ============================================================================

# Check if a service exists
function Verify-ServiceExists
{
    param([string]$ServiceName)

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    return $null -ne $service
}

# Get service status
function Get-ServiceStatus
{
    param([string]$ServiceName)

    try
    {
        $service = Get-Service -Name $ServiceName -ErrorAction Stop
        return $service.Status
    } catch
    {
        return $null
    }
}

# Get service startup type
function Get-ServiceStartupType
{
    param([string]$ServiceName)

    try
    {
        $service = Get-Service -Name $ServiceName -ErrorAction Stop
        return $service.StartType
    } catch
    {
        return $null
    }
}

# Verify service is in expected state
function Verify-ServiceStatus
{
    param(
        [string]$ServiceName,
        [string]$ExpectedStatus
    )

    $status = Get-ServiceStatus -ServiceName $ServiceName
    return $status -eq $ExpectedStatus
}

# Verify service startup type
function Verify-ServiceStartupType
{
    param(
        [string]$ServiceName,
        [string]$ExpectedStartType
    )

    $startType = Get-ServiceStartupType -ServiceName $ServiceName
    return $startType -eq $ExpectedStartType
}

# ============================================================================
# SERVICE CONTROL
# ============================================================================

# Stop a service with verification
function Stop-ServiceVerified
{
    param(
        [string]$ServiceName,
        [switch]$Force
    )

    if (-not (Verify-ServiceExists $ServiceName))
    {
        Log-Debug "$ServiceName does not exist"
        return $true
    }

    $status = Get-ServiceStatus -ServiceName $ServiceName

    if ($status -eq "Stopped")
    {
        Log-Debug "$ServiceName already stopped"
        return $true
    }

    try
    {
        if ($Force)
        {
            Stop-Service -Name $ServiceName -Force -ErrorAction Stop | Out-Null
        } else
        {
            Stop-Service -Name $ServiceName -ErrorAction Stop | Out-Null
        }

        # Wait for service to stop
        $timeout = 30
        $elapsed = 0
        while ((Get-ServiceStatus -ServiceName $ServiceName) -ne "Stopped" -and $elapsed -lt $timeout)
        {
            Start-Sleep -Seconds 1
            $elapsed++
        }

        # Verify
        if (Verify-ServiceStatus -ServiceName $ServiceName -ExpectedStatus "Stopped")
        {
            Log-Debug "$ServiceName stopped"
            return $true
        } else
        {
            Log-Warning "Failed to stop $ServiceName (timeout)"
            return $false
        }
    } catch
    {
        Log-Warning "Failed to stop $ServiceName`: $_"
        return $false
    }
}

# Start a service with verification
function Start-ServiceVerified
{
    param([string]$ServiceName)

    if (-not (Verify-ServiceExists $ServiceName))
    {
        Log-Warning "$ServiceName does not exist"
        return $false
    }

    $status = Get-ServiceStatus -ServiceName $ServiceName

    if ($status -eq "Running")
    {
        Log-Debug "$ServiceName already running"
        return $true
    }

    try
    {
        Start-Service -Name $ServiceName -ErrorAction Stop | Out-Null

        # Wait for service to start
        $timeout = 30
        $elapsed = 0
        while ((Get-ServiceStatus -ServiceName $ServiceName) -ne "Running" -and $elapsed -lt $timeout)
        {
            Start-Sleep -Seconds 1
            $elapsed++
        }

        # Verify
        if (Verify-ServiceStatus -ServiceName $ServiceName -ExpectedStatus "Running")
        {
            Log-Success "$ServiceName started"
            return $true
        } else
        {
            Log-Warning "Failed to start $ServiceName (timeout)"
            return $false
        }
    } catch
    {
        Log-Warning "Failed to start $ServiceName`: $_"
        return $false
    }
}

# Disable a service with verification
function Disable-ServiceVerified
{
    param(
        [string]$ServiceName,
        [string]$Description = ""
    )

    if (-not (Verify-ServiceExists $ServiceName))
    {
        # Service doesn't exist - that's fine for disabling
        return $true
    }

    # Check if already disabled
    if (Verify-ServiceStartupType -ServiceName $ServiceName -ExpectedStartType "Disabled")
    {
        if ($Description)
        {
            Log-Success "$Description (already disabled)"
        } else
        {
            Log-Success "$ServiceName (already disabled)"
        }
        return $true
    }

    try
    {
        # Stop the service first if it's running
        $status = Get-ServiceStatus -ServiceName $ServiceName
        if ($status -eq "Running")
        {
            Stop-ServiceVerified -ServiceName $ServiceName -Force | Out-Null
        }

        # Disable the service
        Set-Service -Name $ServiceName -StartupType Disabled -ErrorAction Stop | Out-Null

        # Verify
        if (Verify-ServiceStartupType -ServiceName $ServiceName -ExpectedStartType "Disabled")
        {
            if ($Description)
            {
                Log-Success "$Description disabled"
            } else
            {
                Log-Success "$ServiceName disabled"
            }
            return $true
        } else
        {
            Log-Warning "Failed to disable $ServiceName"
            return $false
        }
    } catch
    {
        Log-Warning "Failed to disable $ServiceName`: $_"
        return $false
    }
}

# Enable a service with verification
function Enable-ServiceVerified
{
    param(
        [string]$ServiceName,
        [string]$StartupType = "Automatic",
        [switch]$StartNow
    )

    if (-not (Verify-ServiceExists $ServiceName))
    {
        Log-Warning "$ServiceName does not exist"
        return $false
    }

    try
    {
        Set-Service -Name $ServiceName -StartupType $StartupType -ErrorAction Stop | Out-Null

        # Verify startup type
        if (-not (Verify-ServiceStartupType -ServiceName $ServiceName -ExpectedStartType $StartupType))
        {
            Log-Warning "Failed to set $ServiceName startup type"
            return $false
        }

        # Start now if requested
        if ($StartNow)
        {
            return Start-ServiceVerified -ServiceName $ServiceName
        }

        Log-Success "$ServiceName enabled ($StartupType)"
        return $true
    } catch
    {
        Log-Warning "Failed to enable $ServiceName`: $_"
        return $false
    }
}

# ============================================================================
# BLOATWARE SERVICES
# ============================================================================

# Common services to disable for privacy/performance
$BLOATWARE_SERVICES = @(
    @{ Name = "DiagTrack"; Description = "Connected User Experiences and Telemetry" }
    @{ Name = "dmwappushservice"; Description = "WAP Push Message Routing Service" }
    @{ Name = "WSearch"; Description = "Windows Search (if using Everything)" }
    @{ Name = "SysMain"; Description = "Superfetch (unnecessary on SSD)" }
    @{ Name = "XblAuthManager"; Description = "Xbox Live Auth Manager" }
    @{ Name = "XblGameSave"; Description = "Xbox Live Game Save" }
    @{ Name = "XboxGipSvc"; Description = "Xbox Accessory Management" }
    @{ Name = "XboxNetApiSvc"; Description = "Xbox Live Networking" }
)

# Disable bloatware services
function Disable-BloatwareServices
{
    Log-Header "Disabling Bloatware Services"

    $disabled = 0
    $failed = 0

    foreach ($svc in $BLOATWARE_SERVICES)
    {
        if (Disable-ServiceVerified -ServiceName $svc.Name -Description $svc.Description)
        {
            $disabled++
        } else
        {
            $failed++
        }
    }

    if ($failed -gt 0)
    {
        Log-Warning "Disabled $disabled services, $failed failed"
        return $false
    }

    Log-Success "All $disabled bloatware services disabled"
    return $true
}

# ============================================================================
# CONFIG-BASED SERVICE MANAGEMENT
# ============================================================================

# Disable services from config file
function Disable-ServicesFromConfig
{
    Log-Header "Disabling Services (from config)"

    Log-Info "Loading services from config..."
    $servicesConfig = Load-Config "windows-services.txt"

    if (-not $servicesConfig -or $servicesConfig.Count -eq 0)
    {
        Log-Info "No services defined in config"
        return $true
    }

    $disabled = 0
    $skipped = 0
    $failed = 0

    foreach ($line in $servicesConfig)
    {
        if (-not $line -or $line.StartsWith('#'))
        {
            continue
        }

        $parts = $line -split '\|'
        $serviceName = $parts[0]
        $description = if ($parts.Count -ge 2)
        { $parts[1] 
        } else
        { $serviceName 
        }

        if (-not (Verify-ServiceExists $serviceName))
        {
            $skipped++
            continue
        }

        if (Disable-ServiceVerified -ServiceName $serviceName -Description $description)
        {
            $disabled++
        } else
        {
            $failed++
        }
    }

    Log-Info "Disabled: $disabled, Skipped (not found): $skipped, Failed: $failed"

    if ($failed -gt 0)
    {
        return $false
    }

    return $true
}

# ============================================================================
# STATUS
# ============================================================================

# Show services status
function Get-ServicesStatus
{
    Log-Header "Services Status"

    Log-Info "=== Commonly Disabled Services ==="

    foreach ($svc in $BLOATWARE_SERVICES)
    {
        if (-not (Verify-ServiceExists $svc.Name))
        {
            Log-Info "$($svc.Description): not installed"
            continue
        }

        $status = Get-ServiceStatus -ServiceName $svc.Name
        $startType = Get-ServiceStartupType -ServiceName $svc.Name

        if ($startType -eq "Disabled")
        {
            Log-Success "$($svc.Description): Disabled"
        } elseif ($status -eq "Stopped")
        {
            Log-Info "$($svc.Description): Stopped ($startType)"
        } else
        {
            Log-Warning "$($svc.Description): $status ($startType)"
        }
    }
}

# List all running services
function Get-RunningServices
{
    Log-Header "Running Services"

    $services = Get-Service | Where-Object { $_.Status -eq "Running" } | Sort-Object DisplayName

    Log-Info "Total running services: $($services.Count)"
    Log-Info ""

    foreach ($svc in $services)
    {
        Write-Output "$($svc.Name) - $($svc.DisplayName)"
    }
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full services setup
function Setup-Services
{
    $errors = 0

    if (-not (Disable-ServicesFromConfig))
    {
        $errors++
    }

    if ($errors -gt 0)
    {
        Log-Warning "Services setup completed with issues"
        return $false
    }

    Log-Success "Services setup complete"
    return $true
}

# ============================================================================
# EXPORT
# ============================================================================

Export-ModuleMember -Function @(
    'Verify-ServiceExists',
    'Verify-ServiceStatus',
    'Verify-ServiceStartupType',
    'Get-ServiceStatus',
    'Get-ServiceStartupType',
    'Stop-ServiceVerified',
    'Start-ServiceVerified',
    'Disable-ServiceVerified',
    'Enable-ServiceVerified',
    'Disable-BloatwareServices',
    'Disable-ServicesFromConfig',
    'Get-ServicesStatus',
    'Get-RunningServices',
    'Setup-Services'
) -Variable @('BLOATWARE_SERVICES')
