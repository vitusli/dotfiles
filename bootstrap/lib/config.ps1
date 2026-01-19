# ============================================================================
# CONFIG LOADING LIBRARY (PowerShell)
# Shared config loading functions for Windows bootstrap scripts
# ============================================================================

# Config URL (can be overridden)
if (-not $CONFIG_URL)
{
    $CONFIG_URL = "https://raw.githubusercontent.com/vitusli/dotfiles/main/config"
}
$CONFIG_DIR = $null

# ============================================================================
# RAW LOADING
# ============================================================================

# Load raw content from local file or remote URL (fallback)
# Usage: $content = Load-Raw "cli.txt"
function Load-Raw
{
    param([string]$File)

    $localPath = if ($CONFIG_DIR)
    { Join-Path $CONFIG_DIR $File 
    } else
    { $null 
    }

    if ($localPath -and (Test-Path $localPath))
    {
        return Get-Content -Path $localPath -Raw
    } else
    {
        try
        {
            $response = Invoke-WebRequest -Uri "$CONFIG_URL/$File" -UseBasicParsing
            return $response.Content
        } catch
        {
            Write-Warning "Failed to load $File from config: $_"
            return ""
        }
    }
}

# ============================================================================
# PACKAGE LOADING
# ============================================================================

# Load packages for a specific platform
# Filters out packages tagged for other platforms
# Usage: $packages = Load-Packages "cli.txt" "windows"
function Load-Packages
{
    param(
        [string]$File,
        [string]$Platform = "windows"
    )

    $content = Load-Raw $File
    if (-not $content)
    { return @() 
    }

    $otherPlatforms = switch ($Platform)
    {
        "macos"
        { @("linux", "windows") 
        }
        "linux"
        { @("macos", "windows") 
        }
        "windows"
        { @("macos", "linux") 
        }
        default
        { @() 
        }
    }

    $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
        # Skip empty lines and comment-only lines
        $_ -and -not $_.StartsWith('#')
    } | Where-Object {
        $line = $_

        # Include if no platform tag at all
        if ($line -notmatch '#')
        { return $true 
        }

        # Include if has our platform tag
        if ($line -match "#$Platform")
        { return $true 
        }

        # Exclude if has other platform tags but NOT ours
        foreach ($other in $otherPlatforms)
        {
            if ($line -match "#$other")
            { return $false 
            }
        }

        # Include if none of the above matched (generic tag like #comment)
        return $true
    } | ForEach-Object {
        # Strip tags and trailing comments
        $_ -replace '\s*#.*$', ''
    } | Where-Object { $_ }

    return $lines
}

# Load all packages without platform filtering (strips comments)
# Usage: $extensions = Load-AllPackages "vscode.txt"
function Load-AllPackages
{
    param([string]$File)

    $content = Load-Raw $File
    if (-not $content)
    { return @() 
    }

    $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
        $_ -and -not $_.StartsWith('#')
    } | ForEach-Object {
        $_ -replace '\s*#.*$', ''
    } | Where-Object { $_ }

    return $lines
}

# Load config preserving format (for repos, services, registry, etc.)
# Only strips comment lines, keeps inline format like "key|value|extra"
# Usage: $repos = Load-Config "repos.txt"
function Load-Config
{
    param([string]$File)

    $content = Load-Raw $File
    if (-not $content)
    { return @() 
    }

    $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
        $_ -and -not $_.StartsWith('#')
    }

    return $lines
}

# ============================================================================
# SECTION LOADING
# ============================================================================

# Load packages from a specific section in a file
# Sections are marked with #sectionname
# Usage: $nvidia = Load-Section "linux-packages.txt" "nvidia"
function Load-Section
{
    param(
        [string]$File,
        [string]$Section
    )

    $content = Load-Raw $File
    if (-not $content)
    { return @() 
    }

    $lines = $content -split "`n"
    $inSection = $false
    $result = @()

    foreach ($line in $lines)
    {
        $trimmed = $line.Trim()

        if ($trimmed -match "^#$Section\s*$")
        {
            $inSection = $true
            continue
        }

        if ($inSection)
        {
            # End section on next section marker
            if ($trimmed -match '^#[a-zA-Z]' -and $trimmed -notmatch "^#$Section")
            {
                break
            }

            # Skip comments and empty lines
            if ($trimmed -and -not $trimmed.StartsWith('#'))
            {
                $result += $trimmed
            }
        }
    }

    return $result
}

# ============================================================================
# CONFIG PARSING
# ============================================================================

# Parse a pipe-delimited config line into hashtable
# Usage: $parsed = Parse-ConfigLine "app_id|app_name|extra" @("id", "name", "extra")
function Parse-ConfigLine
{
    param(
        [string]$Line,
        [string[]]$Fields
    )

    $parts = $Line -split '\|'
    $result = @{}

    for ($i = 0; $i -lt $Fields.Count; $i++)
    {
        if ($i -lt $parts.Count)
        {
            $result[$Fields[$i]] = $parts[$i]
        } else
        {
            $result[$Fields[$i]] = $null
        }
    }

    return $result
}

# Get a specific field from a pipe-delimited line
# Usage: $appId = Get-ConfigField "app_id|app_name" 0
function Get-ConfigField
{
    param(
        [string]$Line,
        [int]$Index
    )

    $parts = $Line -split '\|'
    if ($Index -lt $parts.Count)
    {
        return $parts[$Index]
    }
    return $null
}

# ============================================================================
# ARRAY HELPERS
# ============================================================================

# Check if item is in array
# Usage: if (Test-InArray "item" $array) { ... }
function Test-InArray
{
    param(
        [string]$Item,
        [array]$Array
    )

    return $Array -contains $Item
}

# ============================================================================
# EXPORT
# ============================================================================

Export-ModuleMember -Function @(
    'Load-Raw',
    'Load-Packages',
    'Load-AllPackages',
    'Load-Config',
    'Load-Section',
    'Parse-ConfigLine',
    'Get-ConfigField',
    'Test-InArray'
) -Variable @('CONFIG_URL', 'CONFIG_DIR')
