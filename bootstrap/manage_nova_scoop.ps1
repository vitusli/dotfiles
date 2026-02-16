#!/usr/bin/env pwsh
# ============================================================================
# Nova-CLI Scoop Bucket Manager
# Manages nova-cli via a local Scoop bucket (like Homebrew!)
# ============================================================================

param(
    [Parameter(Position = 0)]
    [ValidateSet('install', 'update', 'uninstall', 'status', 'setup-bucket')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'

# Configuration
$BUCKET_NAME = "my-bucket"
$BUCKET_PATH = "$HOME\scoop\buckets\$BUCKET_NAME"
$APP_NAME = "nova-cli"
$INSTALL_DIR = "$HOME\NovaCLI"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Status {
    param([string]$Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Info {
    param([string]$Message)
    Write-Host "→ " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

function Get-LatestRelease {
    Write-Info "Fetching latest release from GitHub..."
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/wandelbotsgmbh/nova-cli/releases/latest"
    
    $version = $response.tag_name
    $asset = $response.assets | Where-Object { $_.name -like "novacli_win64-*.zip" } | Select-Object -First 1
    
    if (-not $asset) {
        throw "Windows binary not found in latest release"
    }
    
    return @{
        Version = $version
        Url = $asset.browser_download_url
        Hash = $null  # GitHub doesn't provide hashes, we'll compute it
    }
}

function Get-FileHash256 {
    param([string]$Url)
    
    Write-Info "Computing SHA256 hash..."
    $tempFile = "$env:TEMP\nova-download-$(Get-Random).zip"
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $tempFile -UseBasicParsing
        $hash = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash
        return $hash
    } finally {
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
    }
}

function New-ScoopManifest {
    param(
        [string]$Version,
        [string]$Url,
        [string]$Hash
    )
    
    $manifest = @{
        version = $Version
        description = "Wandelbots Nova CLI"
        homepage = "https://github.com/wandelbotsgmbh/nova-cli"
        license = "Unknown"
        url = $Url
        hash = $Hash
        extract_dir = ""
        bin = "nova.exe"
        checkver = @{
            github = "https://github.com/wandelbotsgmbh/nova-cli"
        }
        autoupdate = @{
            url = "https://github.com/wandelbotsgmbh/nova-cli/releases/download/`$version/novacli_win64-`$version.zip"
        }
    }
    
    return ($manifest | ConvertTo-Json -Depth 10)
}

function Initialize-Bucket {
    Write-Info "Setting up local Scoop bucket..."
    
    # Create bucket directory structure
    if (-not (Test-Path $BUCKET_PATH)) {
        New-Item -ItemType Directory -Path $BUCKET_PATH -Force | Out-Null
        New-Item -ItemType Directory -Path "$BUCKET_PATH\bucket" -Force | Out-Null
    }
    
    # Initialize as git repo if not already
    Push-Location $BUCKET_PATH
    try {
        if (-not (Test-Path ".git")) {
            git init 2>&1 | Out-Null
            Write-Status "Initialized git repository"
        }
    } finally {
        Pop-Location
    }
    
    # Add bucket to scoop if not already added
    $buckets = scoop bucket list
    if ($buckets -notmatch $BUCKET_NAME) {
        scoop bucket add $BUCKET_NAME $BUCKET_PATH
        Write-Status "Added bucket to Scoop"
    } else {
        Write-Status "Bucket already registered"
    }
}

function Update-Manifest {
    Write-Info "Updating manifest with latest release info..."
    
    $release = Get-LatestRelease
    $hash = Get-FileHash256 -Url $release.Url
    
    $manifestPath = "$BUCKET_PATH\bucket\$APP_NAME.json"
    $manifestContent = New-ScoopManifest -Version $release.Version -Url $release.Url -Hash $hash
    
    Set-Content -Path $manifestPath -Value $manifestContent -Encoding UTF8
    Write-Status "Manifest created for version $($release.Version)"
    
    # Commit to git
    Push-Location $BUCKET_PATH
    try {
        git add . 2>&1 | Out-Null
        git commit -m "Update $APP_NAME to $($release.Version)" 2>&1 | Out-Null
    } catch {
        # Ignore git errors
    }
    Pop-Location
    
    return $release.Version
}

function Install-Nova {
    Write-Info "Installing nova-cli via Scoop..."
    
    # Setup bucket first
    Initialize-Bucket
    
    # Update manifest
    $version = Update-Manifest
    
    # Install via scoop
    scoop install "$BUCKET_NAME/$APP_NAME"
    
    Write-Status "Nova-CLI $version installed successfully!"
    Write-Host ""
    Write-Host "Try: " -NoNewline
    Write-Host "nova version" -ForegroundColor Yellow
}

function Update-Nova {
    Write-Info "Updating nova-cli..."
    
    # Update manifest with latest version
    $version = Update-Manifest
    
    # Update via scoop
    scoop update "$APP_NAME"
    
    Write-Status "Nova-CLI updated to $version!"
}

function Uninstall-Nova {
    Write-Info "Uninstalling nova-cli..."
    
    scoop uninstall "$APP_NAME"
    
    Write-Status "Nova-CLI uninstalled"
    
    # Optionally remove the old manual installation
    if (Test-Path $INSTALL_DIR) {
        Write-Host ""
        Write-Host "Old manual installation found at: " -NoNewline
        Write-Host $INSTALL_DIR -ForegroundColor Yellow
        $remove = Read-Host "Remove it? (y/n)"
        if ($remove -eq 'y') {
            Remove-Item -Path $INSTALL_DIR -Recurse -Force
            Write-Status "Removed old installation"
        }
    }
}

function Show-Status {
    Write-Host ""
    Write-Host "Nova-CLI Status" -ForegroundColor Cyan
    Write-Host "===============" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if scoop is available
    if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
        Write-Error "Scoop is not installed"
        return
    }
    Write-Status "Scoop is installed"
    
    # Check if bucket exists
    $buckets = scoop bucket list
    if ($buckets -match $BUCKET_NAME) {
        Write-Status "Bucket '$BUCKET_NAME' is registered"
    } else {
        Write-Host "  Bucket '$BUCKET_NAME' not registered" -ForegroundColor Yellow
    }
    
    # Check if nova-cli is installed
    $apps = scoop list
    if ($apps -match $APP_NAME) {
        $info = scoop info $APP_NAME
        Write-Status "Nova-CLI is installed"
        
        # Try to get version
        try {
            $version = & nova version 2>&1
            Write-Host "  Version: " -NoNewline
            Write-Host $version -ForegroundColor Green
        } catch {
            Write-Host "  (unable to get version)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Nova-CLI is not installed" -ForegroundColor Yellow
    }
    
    # Check for old manual installation
    if (Test-Path $INSTALL_DIR) {
        Write-Host ""
        Write-Host "  Note: Old manual installation found at $INSTALL_DIR" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  .\manage_nova_scoop.ps1 install    - Install nova-cli"
    Write-Host "  .\manage_nova_scoop.ps1 update     - Update to latest version"
    Write-Host "  .\manage_nova_scoop.ps1 uninstall  - Uninstall nova-cli"
    Write-Host "  .\manage_nova_scoop.ps1 status     - Show this status"
    Write-Host ""
}

function Setup-Bucket {
    Initialize-Bucket
    Update-Manifest | Out-Null
    Write-Status "Bucket setup complete!"
}

# ============================================================================
# Main
# ============================================================================

try {
    switch ($Action) {
        'install' {
            Install-Nova
        }
        'update' {
            Update-Nova
        }
        'uninstall' {
            Uninstall-Nova
        }
        'setup-bucket' {
            Setup-Bucket
        }
        'status' {
            Show-Status
        }
    }
} catch {
    Write-Host ""
    Write-Error "Error: $($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    exit 1
}
