# ============================================================================
# LOGGING LIBRARY (PowerShell)
# Shared logging functions for Windows bootstrap scripts
# ============================================================================

# Log file (can be overridden by sourcing script)
if (-not $LOG_FILE)
{
    $LOG_FILE = "$env:TEMP\bootstrap-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
}

# ============================================================================
# CORE LOGGING FUNCTIONS
# ============================================================================

function Log-Header
{
    param([string]$Message)

    $output = @"

════════════════════════════════════════════════════════════
▶ $Message
════════════════════════════════════════════════════════════
"@

    Write-Host $output -ForegroundColor Cyan
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Success
{
    param([string]$Message)

    $output = "✓ $Message"
    Write-Host $output -ForegroundColor Green
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Info
{
    param([string]$Message)

    $output = "ℹ $Message"
    Write-Host $output
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Warning
{
    param([string]$Message)

    $output = "⚠ $Message"
    Write-Host $output -ForegroundColor Yellow
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Error
{
    param([string]$Message)

    $output = "✗ $Message"
    Write-Host $output -ForegroundColor Red
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Debug
{
    param([string]$Message)

    $output = "  → $Message"
    if ($env:DEBUG -eq "true")
    {
        Write-Host $output -ForegroundColor Blue
    }
    Add-Content -Path $LOG_FILE -Value $output
}

# ============================================================================
# VERIFICATION HELPERS
# These functions perform actual verification instead of trusting exit codes
# ============================================================================

# Verify a command exists
# Usage: if (Verify-Command "git") { Log-Success "git available" }
function Verify-Command
{
    param([string]$Command)

    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Verify a file exists
# Usage: if (Verify-File "$HOME\.zshrc") { Log-Success ".zshrc exists" }
function Verify-File
{
    param([string]$Path)

    return Test-Path -Path $Path -PathType Leaf
}

# Verify a directory exists
# Usage: if (Verify-Directory "$HOME\.config") { Log-Success ".config exists" }
function Verify-Directory
{
    param([string]$Path)

    return Test-Path -Path $Path -PathType Container
}

# Verify a registry value exists and optionally matches expected value
# Usage: Verify-RegistryValue "HKCU:\Software\Test" "ValueName" 1
function Verify-RegistryValue
{
    param(
        [string]$Path,
        [string]$Name,
        $ExpectedValue = $null
    )

    try
    {
        $value = Get-ItemPropertyValue -Path $Path -Name $Name -ErrorAction Stop

        if ($null -ne $ExpectedValue)
        {
            return $value -eq $ExpectedValue
        }
        return $true
    } catch
    {
        return $false
    }
}

# Verify a service is in expected state
# Usage: Verify-ServiceState "wuauserv" "Stopped"
function Verify-ServiceState
{
    param(
        [string]$ServiceName,
        [string]$ExpectedStatus = "Running"
    )

    try
    {
        $service = Get-Service -Name $ServiceName -ErrorAction Stop
        return $service.Status -eq $ExpectedStatus
    } catch
    {
        return $false
    }
}

# Verify a service startup type
# Usage: Verify-ServiceStartup "wuauserv" "Disabled"
function Verify-ServiceStartup
{
    param(
        [string]$ServiceName,
        [string]$ExpectedStartType = "Automatic"
    )

    try
    {
        $service = Get-Service -Name $ServiceName -ErrorAction Stop
        return $service.StartType -eq $ExpectedStartType
    } catch
    {
        return $false
    }
}

# Verify an AppX package is NOT installed (for bloatware removal)
# Usage: Verify-AppxRemoved "Microsoft.BingWeather"
function Verify-AppxRemoved
{
    param([string]$PackageName)

    $packages = @(Get-AppxPackage -Name $PackageName -AllUsers -ErrorAction SilentlyContinue)
    return $packages.Count -eq 0
}

# Verify a Scoop package is installed
# Usage: Verify-ScoopPackage "git"
function Verify-ScoopPackage
{
    param([string]$PackageName)

    $result = @(scoop list $PackageName 2>$null | Where-Object { $_.Name -eq $PackageName })
    return $result.Count -gt 0
}

# Verify environment variable is set
# Usage: Verify-EnvVar "EDITOR"
function Verify-EnvVar
{
    param(
        [string]$Name,
        [string]$ExpectedValue = $null
    )

    $value = [Environment]::GetEnvironmentVariable($Name)

    if ($null -eq $value)
    {
        return $false
    }

    if ($null -ne $ExpectedValue)
    {
        return $value -eq $ExpectedValue
    }

    return $true
}

# ============================================================================
# PLATFORM DETECTION
# ============================================================================

function Get-OSInfo
{
    return @{
        OS      = "windows"
        Version = [System.Environment]::OSVersion.VersionString
        Arch    = if ([Environment]::Is64BitOperatingSystem)
        { "amd64" 
        } else
        { "x86" 
        }
        User    = $env:USERNAME
        Host    = $env:COMPUTERNAME
    }
}

function Test-Administrator
{
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ============================================================================
# EXECUTION HELPERS
# ============================================================================

# Run a command and verify its result with a custom check
# Usage: Invoke-AndVerify "Installing git" { scoop install git } { Verify-Command "git" }
function Invoke-AndVerify
{
    param(
        [string]$Description,
        [scriptblock]$Command,
        [scriptblock]$VerifyBlock = $null
    )

    Log-Info "$Description..."

    try
    {
        $output = & $Command 2>&1 | Out-String

        # Log command output
        Add-Content -Path $LOG_FILE -Value "Command: $($Command.ToString())"
        Add-Content -Path $LOG_FILE -Value "Output: $output"

        # Verify with custom check if provided
        if ($null -ne $VerifyBlock)
        {
            if (& $VerifyBlock)
            {
                Log-Success $Description
                return $true
            } else
            {
                Log-Error "$Description - verification failed"
                return $false
            }
        } else
        {
            Log-Success $Description
            return $true
        }
    } catch
    {
        Log-Error "$Description - $($_.Exception.Message)"
        Add-Content -Path $LOG_FILE -Value "Error: $($_.Exception.Message)"
        return $false
    }
}

# Run a command silently, only log on error
# Usage: Invoke-Silent { git pull }
function Invoke-Silent
{
    param([scriptblock]$Command)

    try
    {
        $output = & $Command 2>&1 | Out-String
        return $true
    } catch
    {
        Add-Content -Path $LOG_FILE -Value "Command failed: $($Command.ToString())"
        Add-Content -Path $LOG_FILE -Value "Error: $($_.Exception.Message)"
        return $false
    }
}

# ============================================================================
# INITIALIZATION
# ============================================================================

function Initialize-Logging
{
    $logDir = Split-Path -Parent $LOG_FILE
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null

    $osInfo = Get-OSInfo

    $header = @"
════════════════════════════════════════════════════════════
Bootstrap Log
════════════════════════════════════════════════════════════
Start Time: $(Get-Date)
OS: $($osInfo.OS)
Version: $($osInfo.Version)
Arch: $($osInfo.Arch)
User: $($osInfo.User)
Host: $($osInfo.Host)
Administrator: $(Test-Administrator)
════════════════════════════════════════════════════════════

"@

    Add-Content -Path $LOG_FILE -Value $header -Force
    Log-Info "Log file: $LOG_FILE"
}

# Export functions for module use
Export-ModuleMember -Function @(
    'Log-Header',
    'Log-Success',
    'Log-Info',
    'Log-Warning',
    'Log-Error',
    'Log-Debug',
    'Verify-Command',
    'Verify-File',
    'Verify-Directory',
    'Verify-RegistryValue',
    'Verify-ServiceState',
    'Verify-ServiceStartup',
    'Verify-AppxRemoved',
    'Verify-ScoopPackage',
    'Verify-EnvVar',
    'Get-OSInfo',
    'Test-Administrator',
    'Invoke-AndVerify',
    'Invoke-Silent',
    'Initialize-Logging'
) -Variable @('LOG_FILE')
