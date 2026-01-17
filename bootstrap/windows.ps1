# windowme.ps1 - Windows Setup & Configuration Script
# Download and run with PowerShell:
# curl -fsSL https://github.com/vitusli/wotfiles/blob/master/wina.ps1 | powershell -c "$input | iex"


#Requires -RunAsAdministrator

# ============================================================================
# CONFIGURATION
# ============================================================================

$LOG_DIR = "$PSScriptRoot\logs"
$LOG_FILE = "$LOG_DIR\wina-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$CONFIG_URL = "https://raw.githubusercontent.com/vitusli/dotfiles/main/config"

# Use explicit English path to avoid localized folder names (e.g., "Dokumente" on German Windows)
$DOCUMENTS = "$HOME\Documents"

# ============================================================================
# CONFIG LOADING FUNCTIONS
# ============================================================================

function Load-Packages {
    param(
        [string]$File,
        [string]$Platform = "windows"
    )

    $url = "$CONFIG_URL/$File"

    try {
        $content = (Invoke-WebRequest -Uri $url -UseBasicParsing).Content
        $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -and -not $_.StartsWith('#')
        } | Where-Object {
            # Include if: no tag at all
            if ($_ -notmatch '#') { return $true }
            # Include if: has our platform tag
            if ($_ -match "#$Platform") { return $true }
            # Exclude if: has other platform tags but NOT ours
            return $false
        } | ForEach-Object {
            # Strip tags
            $_ -replace '\s*#.*$', ''
        }
        return $lines
    } catch {
        Log-Warning "Failed to load $File from config: $_"
        return @()
    }
}

function Load-AllPackages {
    param([string]$File)

    $url = "$CONFIG_URL/$File"

    try {
        $content = (Invoke-WebRequest -Uri $url -UseBasicParsing).Content
        $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -and -not $_.StartsWith('#')
        } | ForEach-Object {
            $_ -replace '\s*#.*$', ''
        }
        return $lines
    } catch {
        Log-Warning "Failed to load $File from config: $_"
        return @()
    }
}

function Load-Config {
    param([string]$File)

    $url = "$CONFIG_URL/$File"

    try {
        $content = (Invoke-WebRequest -Uri $url -UseBasicParsing).Content
        $lines = $content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -and -not $_.StartsWith('#')
        }
        return $lines
    } catch {
        Log-Warning "Failed to load $File from config: $_"
        return @()
    }
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

# Windows-specific packages are now in cli.txt and gui.txt with #windows tag

# ============================================================================
# REGISTRY CONFIGURATIONS (Remove Consumer Bloat)
# ============================================================================

# Registry tweaks are now loaded from config/windows-registry.txt

# ============================================================================
# SERVICES TO DISABLE
# ============================================================================

# Services and bloatware are now loaded from config files:
# - config/windows-services.txt
# - config/windows-bloatware.txt

# ============================================================================
# WINDOWS FEATURES TO DISABLE
# ============================================================================

$FEATURES_TO_DISABLE = @(
    "XPS-Viewer"
    "WindowsMediaPlayer"
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Initialize-Logging {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

    $header = @"
════════════════════════════════════════════════════════════
Windows Setup & Configuration Script Log
════════════════════════════════════════════════════════════
Start Time: $(Get-Date)
Log File: $LOG_FILE
User: $env:USERNAME
Hostname: $env:COMPUTERNAME
Windows Version: $([System.Environment]::OSVersion.VersionString)
════════════════════════════════════════════════════════════

"@

    Add-Content -Path $LOG_FILE -Value $header -Force
    Write-Output $header
}

function Log-Header {
    param([string]$Message)

    $output = @"

════════════════════════════════════════════════════════════
▶ $Message
════════════════════════════════════════════════════════════
"@

    Write-Output $output
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Success {
    param([string]$Message)

    $output = "✓ $Message"
    Write-Host $output -ForegroundColor Green
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Info {
    param([string]$Message)

    $output = "ℹ $Message"
    Write-Output $output
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Warning {
    param([string]$Message)

    $output = "⚠ $Message"
    Write-Host $output -ForegroundColor Yellow
    Add-Content -Path $LOG_FILE -Value $output
}

function Log-Error {
    param([string]$Message)

    $output = "✗ $Message"
    Write-Host $output -ForegroundColor Red
    Add-Content -Path $LOG_FILE -Value $output
}

function Test-Administrator {
    $admin = [Security.Principal.WindowsIdentity]::GetCurrent() |
        Select-Object -ExpandProperty Groups |
        Select-Object -ExpandProperty Value |
        Where-Object { $_ -eq 'S-1-5-32-544' }

    return $null -ne $admin
}

function Command-Exists {
    param([string]$Command)

    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# ============================================================================
# SCOOP SETUP
# ============================================================================

function Setup-Scoop {
    Log-Header "Setting up Scoop"

    if (Command-Exists scoop) {
        Log-Success "Scoop already installed"
        return
    }

    Log-Info "Installing Scoop..."

    # Set execution policy for current user
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force | Out-Null

    # Install Scoop
    $scoopInstall = @"
iwr -useb get.scoop.sh | iex
"@

    Invoke-Expression $scoopInstall

    if (Command-Exists scoop) {
        Log-Success "Scoop installed"
    } else {
        Log-Error "Failed to install Scoop"
        return $false
    }

    return $true
}

function Add-ScoopBuckets {
    Log-Header "Adding Scoop Buckets"

    foreach ($bucket in $SCOOP_BUCKETS) {
        $existing = scoop bucket list | Select-String $bucket

        if ($existing) {
            Log-Success "Bucket '$bucket' already added"
        } else {
            Log-Info "Adding bucket: $bucket"
            scoop bucket add $bucket
            Log-Success "Bucket '$bucket' added"
        }
    }
}

function Install-ScoopPackages {
    Log-Header "Installing Scoop Packages"

    Log-Info "Loading packages from config..."
    $cliPackages = Load-Packages "cli.txt" "windows"
    $guiPackages = Load-Packages "gui.txt" "windows"

    $allPackages = $cliPackages + $guiPackages

    $toInstall = @()

    foreach ($package in $allPackages) {
        $result = @(scoop list $package 2>$null | Where-Object { $_.Name -eq $package })

        if ($result.Count -gt 0) {
            Log-Success "$package"
        } else {
            Log-Warning "$package (will be installed)"
            $toInstall += $package
        }
    }

    if ($toInstall.Count -gt 0) {
        Log-Info "Installing $($toInstall.Count) packages..."

        foreach ($package in $toInstall) {
            Log-Info "Installing: $package"
            scoop install $package
            Log-Success "Installed: $package"
        }
    } else {
        Log-Info "All packages already installed"
    }
}

# ============================================================================
# GITHUB SETUP
# ============================================================================

function Setup-GitHubAuth {
    Log-Header "Setting up GitHub Authentication"

    if (-not (Command-Exists gh)) {
        Log-Error "GitHub CLI (gh) not found"
        return $false
    }

    $authStatus = & gh auth status 2>&1

    if ($?) {
        Log-Success "GitHub CLI already authenticated"
        return $true
    }

    Log-Info "Authenticating with GitHub CLI..."
    & gh auth login --scopes repo --web

    Log-Success "GitHub authentication complete"
    return $true
}

function Setup-SSHKey {
    Log-Header "Setting up SSH Key"

    $sshKey = "$HOME\.ssh\id_ed25519"

    if (Test-Path $sshKey) {
        Log-Success "SSH key already exists"
        return $true
    }

    Log-Info "Generating SSH key..."

    New-Item -ItemType Directory -Path "$HOME\.ssh" -Force | Out-Null

    ssh-keygen -t ed25519 -C "vituspach@gmail.com" -f $sshKey -N "" | Out-Null

    if (Command-Exists gh) {
        Log-Info "Adding SSH key to GitHub..."
        & gh ssh-key add "$sshKey.pub" --title "Windows $(Get-Date -Format 'yyyy-MM-dd')"
    }

    Log-Success "SSH key created and configured"
    return $true
}

# ============================================================================
# REPOSITORIES
# ============================================================================

function Clone-Repositories {
    Log-Header "Cloning GitHub Repositories"

    Log-Info "Loading repositories from config..."
    $repos = Load-Config "repos.txt"

    foreach ($repoLine in $repos) {
        $parts = $repoLine -split '\|'
        $repo = $parts[0]
        $pathTemplate = $parts[1]

        # Expand variables
        $path = $pathTemplate -replace '\$HOME', $HOME -replace '\$DOCUMENTS', $DOCUMENTS

        $repoName = $repo.Split('/')[-1]
        $fullPath = Join-Path $path $repoName

        if (Test-Path $fullPath) {
            Log-Success "$repoName (already cloned)"
        } else {
            Log-Info "Cloning $repoName to $path..."
            New-Item -ItemType Directory -Path $path -Force | Out-Null

            gh repo clone $repo $fullPath

            Log-Success "$repoName cloned"
        }
    }
}

# ============================================================================
# DOTFILES
# ============================================================================

function Apply-Dotfiles {
    Log-Header "Applying Dotfiles with chezmoi"

    if (-not (Command-Exists chezmoi)) {
        Log-Error "chezmoi not found"
        return $false
    }

    $chezmoiSource = "$HOME\.local\share\chezmoi"

    # Check if already initialized with correct branch
    if (Test-Path "$chezmoiSource\.git") {
        Push-Location $chezmoiSource
        $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
        Pop-Location

        if ($currentBranch -eq "windows") {
            Log-Info "chezmoi already initialized on windows branch, updating..."
            & chezmoi update --apply
            if ($LASTEXITCODE -eq 0) {
                Log-Success "Dotfiles updated successfully"
                return $true
            }
        } else {
            Log-Info "Switching chezmoi to windows branch..."
            Push-Location $chezmoiSource
            git fetch origin windows 2>$null
            git checkout windows 2>$null
            Pop-Location
        }
    }

    # Fresh init or apply after branch switch
    Log-Info "Initializing and applying dotfiles..."
    & chezmoi init --branch windows --apply vitusli/dotfiles
    if ($LASTEXITCODE -eq 0) {
        Log-Success "Dotfiles applied successfully"
    } else {
        Log-Error "Failed to initialize chezmoi"
        return $false
    }

    return $true
}

# ============================================================================
# REGISTRY TWEAKS
# ============================================================================

function Apply-RegistryTweaks {
    Log-Header "Applying Registry Tweaks (from config)"

    Log-Info "Loading registry tweaks from config..."
    $registryConfig = Load-Config "windows-registry.txt"

    foreach ($line in $registryConfig) {
        if (-not $line -or $line.StartsWith('#')) { continue }

        $parts = $line -split '\|'
        if ($parts.Count -lt 4) { continue }

        $path = $parts[0]
        $name = $parts[1]
        $type = $parts[2]
        $valueStr = $parts[3]

        try {
            # Create path if it doesn't exist
            if (-not (Test-Path $path)) {
                New-Item -Path $path -Force | Out-Null
            }

            # Parse value based on type
            switch ($type) {
                "DWORD" {
                    $value = [int]$valueStr
                    Set-ItemProperty -Path $path -Name $name -Value $value -Type DWord -Force | Out-Null
                }
                "String" {
                    Set-ItemProperty -Path $path -Name $name -Value $valueStr -Type String -Force | Out-Null
                }
                "Binary" {
                    # Parse comma-separated hex bytes
                    $bytes = $valueStr -split ',' | ForEach-Object { [byte]"0x$_" }
                    Set-ItemProperty -Path $path -Name $name -Value ([byte[]]$bytes) -Force | Out-Null
                }
                default {
                    Log-Warning "Unknown type: $type for $name"
                }
            }
            Log-Info "$name configured"
        }
        catch {
            Log-Warning "Failed to set $name`: $_"
        }
    }

    Log-Success "Registry tweaks applied"
}

# ============================================================================
# SERVICES
# ============================================================================

function Disable-Services {
    Log-Header "Disabling Unnecessary Services"

    Log-Info "Loading services from config..."
    $servicesConfig = Load-Config "windows-services.txt"

    foreach ($line in $servicesConfig) {
        if (-not $line -or $line.StartsWith('#')) { continue }

        $parts = $line -split '\|'
        $service = $parts[0]

        try {
            $serviceObj = Get-Service -Name $service -ErrorAction SilentlyContinue

            if (-not $serviceObj) {
                continue  # Service doesn't exist, skip silently
            }

            if ($serviceObj.Status -eq "Running") {
                Stop-Service -Name $service -Force -ErrorAction SilentlyContinue | Out-Null
                if ($?) {
                    Log-Info "Stopped $service"
                }
            }

            Set-Service -Name $service -StartupType Disabled -ErrorAction Stop | Out-Null
            Log-Success "Disabled $service"
        }
        catch {
            Log-Warning "Failed to disable $service`: $_"
        }
    }
}

# ============================================================================
# WINDOWS FEATURES
# ============================================================================

function Disable-WindowsFeatures {
    Log-Header "Disabling Windows Features"

    foreach ($feature in $FEATURES_TO_DISABLE) {
        try {
            $featureObj = Get-WindowsOptionalFeature -FeatureName $feature -Online -ErrorAction SilentlyContinue

            if ($featureObj -and $featureObj.State -eq "Enabled") {
                Log-Info "Disabling $feature..."
                Disable-WindowsOptionalFeature -FeatureName $feature -Online -NoRestart | Out-Null
                Log-Success "Disabled $feature"
            } else {
                Log-Success "$feature already disabled"
            }
        }
        catch {
            Log-Warning "Failed to disable $feature`: $_"
        }
    }
}

# ============================================================================
# UNINSTALL BLOATWARE
# ============================================================================

function Remove-Bloatware {
    Log-Header "Removing Windows Bloatware"

    Log-Info "Loading bloatware list from config..."
    $bloatwareApps = Load-Config "windows-bloatware.txt"

    foreach ($app in $bloatwareApps) {
        if (-not $app -or $app.StartsWith('#')) { continue }

        try {
            # Remove for all users
            $packages = @(Get-AppxPackage -Name $app -AllUsers -ErrorAction SilentlyContinue)
            if ($packages.Count -gt 0) {
                Log-Info "Removing $app..."
                Get-AppxPackage -Name $app -AllUsers | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
                Log-Success "Removed $app"
            }

            # Remove provisioned package (prevents reinstall)
            $provisioned = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq $app }
            if ($provisioned) {
                $provisioned | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Out-Null
                Log-Info "Removed provisioned package: $app"
            }
        }
        catch {
            Log-Warning "Could not remove $app`: $_"
        }
    }
}

# ============================================================================
# WGET DOWNLOADS
# ============================================================================

function Install-WgetPackages {
    Log-Header "Downloading and Installing wget packages"

    Log-Info "Loading wget URLs from config..."
    $wgetUrls = Load-Packages "wget.txt" "windows"

    $downloadPath = "$HOME\Downloads"

    foreach ($line in $wgetUrls) {
        if (-not $line -or $line.StartsWith('#')) { continue }

        $parts = $line -split '\|'
        $url = $parts[0]

        # Extract filename from URL or use custom name
        if ($parts.Count -ge 2 -and $parts[1]) {
            $filename = $parts[1]
        } else {
            $filename = [System.IO.Path]::GetFileName($url)
        }

        $filePath = Join-Path $downloadPath $filename

        try {
            # Check if file already exists
            if (Test-Path $filePath) {
                Log-Success "$filename already downloaded"
            } else {
                Log-Info "Downloading $filename..."
                Invoke-WebRequest -Uri $url -OutFile $filePath -UseBasicParsing
                Log-Success "Downloaded $filename"
            }

            # Install if it's an MSI or EXE
            $extension = [System.IO.Path]::GetExtension($filename).ToLower()

            if ($extension -eq ".msi") {
                Log-Info "Installing $filename..."
                Start-Process msiexec.exe -ArgumentList "/i `"$filePath`" /quiet /norestart" -Wait -NoNewWindow
                Log-Success "Installed $filename"
            } elseif ($extension -eq ".exe") {
                Log-Info "Installing $filename..."
                Start-Process -FilePath $filePath -ArgumentList "/S" -Wait -NoNewWindow
                Log-Success "Installed $filename"
            }
        }
        catch {
            Log-Warning "Failed to download/install $filename`: $_"
        }
    }
}

# ============================================================================
# VS CODE EXTENSIONS
# ============================================================================

function Install-VSCodeExtensions {
    Log-Header "Installing VS Code Extensions"

    if (-not (Command-Exists code)) {
        Log-Warning "VS Code not installed, skipping extensions"
        return
    }

    Log-Info "Loading VS Code extensions from config..."
    $extensions = Load-AllPackages "vscode.txt"

    $installed = & code --list-extensions 2>$null
    $toInstall = @()

    foreach ($extension in $extensions) {
        if ($installed -match [regex]::Escape($extension)) {
            Log-Info "Already installed: $extension"
        } else {
            Log-Info "Queued: $extension"
            $toInstall += $extension
        }
    }

    if ($toInstall.Count -gt 0) {
        foreach ($extension in $toInstall) {
            Log-Info "Installing: $extension"
            & code --install-extension $extension | Out-Null
            Log-Success "Installed: $extension"
        }
    } else {
        Log-Info "All VS Code extensions already installed"
    }
}

# ============================================================================
# SYSTEM DEFAULTS
# ============================================================================

function Apply-SystemDefaults {
    Log-Header "Configuring System Defaults"

    try {
        # File Explorer settings
        # Show file extensions
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "HideFileExt" -Value 0 -Type DWORD -Force | Out-Null

        # Show hidden files
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Hidden" -Value 1 -Type DWORD -Force | Out-Null

        # Show system files
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ShowSuperHidden" -Value 1 -Type DWORD -Force | Out-Null

        # Explorer opens in User Home Directory
        Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "LaunchTo" -Force -ErrorAction SilentlyContinue | Out-Null

        # Disable web search in Start Menu
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "BingSearchEnabled" -Value 0 -Type DWORD -Force | Out-Null

        # Use Dark Mode
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" -Name "AppsUseLightTheme" -Value 0 -Type DWORD -Force | Out-Null

        Log-Success "System defaults applied"
    }
    catch {
        Log-Warning "Failed to apply some system defaults: $_"
    }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

function Main {
    Log-Header "Windows Setup & Configuration Script (Idempotent)"

    Write-Output "Starting setup... This may take a while."
    Write-Output "This script can be run multiple times safely."
    Write-Output ""
    Log-Info "Log file: $LOG_FILE"

    # Check admin privileges
    if (-not (Test-Administrator)) {
        Log-Error "This script must be run as Administrator"
        exit 1
    }

    Log-Success "Running as Administrator"

    # Scoop setup
    Setup-Scoop
    Add-ScoopBuckets
    Install-ScoopPackages

    # GitHub
    Setup-GitHubAuth
    Setup-SSHKey
    Clone-Repositories

    # Dotfiles
    Apply-Dotfiles

    # Cleanup & tweaks
    Remove-Bloatware
    Disable-WindowsFeatures
    Disable-Services
    Apply-RegistryTweaks
    Apply-SystemDefaults

    # VS Code
    Install-VSCodeExtensions

    # Wget downloads
    Install-WgetPackages

    # Final summary
    Log-Header "Setup Complete!"

    $endTime = Get-Date
    $success = "✓ All tasks completed successfully!"
    Write-Host $success -ForegroundColor Green
    Add-Content -Path $LOG_FILE -Value $success

    Write-Output ""
    Write-Output "════════════════════════════════════════════════════════════"
    Write-Output "End Time: $endTime"
    Write-Output "════════════════════════════════════════════════════════════"
    Add-Content -Path $LOG_FILE -Value "End Time: $endTime`n════════════════════════════════════════════════════════════"
}

# Run main function
try {
    Initialize-Logging
    Main
} catch {
    Log-Error "Fatal error: $_"
    exit 1
}
