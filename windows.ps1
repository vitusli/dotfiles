# windowme.ps1 - Windows Setup & Configuration Script
# Download and run with PowerShell: 
# curl -fsSL https://github.com/vitusli/wotfiles/blob/master/wina.ps1 | powershell -c "$input | iex"


#Requires -RunAsAdministrator

# ============================================================================
# CONFIGURATION
# ============================================================================

$LOG_DIR = "$HOME\.local\logs"
$LOG_FILE = "$LOG_DIR\wina-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$CONFIG_URL = "https://raw.githubusercontent.com/vitusli/dotfiles/main/config"

# Language-independent special folders
$DOCUMENTS = [Environment]::GetFolderPath('MyDocuments')

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

# ============================================================================
# WINDOWS-SPECIFIC PACKAGES (not in shared config)
# ============================================================================

$WINDOWS_SPECIFIC = @(
    # Core (aria2 makes Scoop downloads faster)
    "7zip"
    "aria2"
    "git-lfs"
    
    # CLI Tools
    "fd"
    "gsudo"
    "scoop-completion"
    
    # Media
    "vlc"
    
    # Fonts (nerd-fonts bucket)
    "JetBrainsMono-NF"
    "FiraCode-NF"
)

# ============================================================================
# REGISTRY CONFIGURATIONS (Remove Consumer Bloat)
# ============================================================================

$REGISTRY_TWEAKS = @(
    # Enable Developer Mode (allows symlinks without admin)
    @{ Path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"; Name = "AllowDevelopmentWithoutDevLicense"; Value = 1; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # TELEMETRY & PRIVACY (Tiny11-Style)
    # ══════════════════════════════════════════════════════════════
    
    # Disable Telemetry completely
    @{ Path = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"; Name = "AllowTelemetry"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Diagnostics\DiagTrack"; Name = "ShowDiagTrackedNotifications"; Value = 0; Type = "DWORD" }
    
    # Disable Advertising ID
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"; Name = "Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKLM:\Software\Policies\Microsoft\Windows\AdvertisingInfo"; Name = "DisabledForUser"; Value = 1; Type = "DWORD" }
    
    # Disable Tailored Experiences
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy"; Name = "TailoredExperiencesWithDiagnosticDataEnabled"; Value = 0; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # SPONSORED APPS & CONTENT DELIVERY (Tiny11-Style)
    # ══════════════════════════════════════════════════════════════
    
    # Disable all Content Delivery (prevents auto-install of sponsored apps)
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "ContentDeliveryAllowed"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "OemPreInstalledAppsEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "PreInstalledAppsEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "PreInstalledAppsEverEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SilentInstalledAppsEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SoftLandingEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SubscribedContentEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SubscribedContent-338388Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SubscribedContent-338389Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SubscribedContent-353694Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SubscribedContent-353696Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "SystemPaneSuggestionsEnabled"; Value = 0; Type = "DWORD" }
    
    # Disable News and Interests
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name = "NewsAndInterestsEnabled"; Value = 0; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # XBOX & GAMING
    # ══════════════════════════════════════════════════════════════
    
    # Disable Xbox Game Bar
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR"; Name = "AppCaptureEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\System\GameConfigStore"; Name = "GameDVR_Enabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR"; Name = "GameDVR_DXGIHotKeyEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\Xbox.App"; Name = "Enabled"; Value = 0; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # CORTANA & SEARCH
    # ══════════════════════════════════════════════════════════════
    
    # Disable Cortana
    @{ Path = "HKCU:\Software\Microsoft\Personalization\Settings"; Name = "AcceptedPrivacyPolicy"; Value = 0; Type = "DWORD" }
    @{ Path = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search"; Name = "AllowCortana"; Value = 0; Type = "DWORD" }
    
    # Disable Bing Search in Start Menu
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"; Name = "BingSearchEnabled"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"; Name = "AllowSearchToUseLocation"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Policies\Microsoft\Windows\Explorer"; Name = "DisableSearchBoxSuggestions"; Value = 1; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # UI & EXPLORER
    # ══════════════════════════════════════════════════════════════
    
    # Disable Windows Tips
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; Name = "ShowSyncProviderNotifications"; Value = 0; Type = "DWORD" }
    
    # Remove Shortcut Arrow Overlay
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"; Name = "29"; Value = ""; Type = "String" }
    
    # Disable Gallery in Explorer
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; Name = "LaunchTo"; Value = 1; Type = "DWORD" }
    @{ Path = "HKLM:\Software\Policies\Microsoft\Windows\Explorer"; Name = "DisableGallery"; Value = 1; Type = "DWORD" }
    
    # ══════════════════════════════════════════════════════════════
    # ANIMATIONS (Disable All)
    # ══════════════════════════════════════════════════════════════
    
    @{ Path = "HKCU:\Control Panel\Desktop"; Name = "UserPreferencesMask"; Value = [byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00); Type = "Binary" }
    @{ Path = "HKCU:\Control Panel\Desktop\WindowMetrics"; Name = "MinAnimate"; Value = "0"; Type = "String" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; Name = "TaskbarAnimations"; Value = 0; Type = "DWORD" }
    @{ Path = "HKCU:\Software\Microsoft\Windows\DWM"; Name = "EnableAeroPeek"; Value = 0; Type = "DWORD" }
)

# ============================================================================
# SERVICES TO DISABLE
# ============================================================================

$SERVICES_TO_DISABLE = @(
    # Telemetry & Diagnostics
    "DiagTrack"                    # Connected User Experiences and Telemetry
    "dmwappushservice"             # WAP Push Message Routing Service
    "diagnosticshub.standardcollector.service"  # Diagnostics Hub
    
    # Xbox Services
    "XblAuthManager"               # Xbox Live Auth Manager
    "XblGameSave"                  # Xbox Live Game Save Service
    "XboxNetApiSvc"                # Xbox Live Networking Service
    "XboxGipSvc"                   # Xbox Accessory Management Service
    
    # Other Bloat
    "HomeGroupListener"            # HomeGroup Listener
    "HomeGroupProvider"            # HomeGroup Provider
    "SharedAccess"                 # Internet Connection Sharing
    "WMPNetworkSvc"                # Windows Media Player Network Sharing
    "RemoteRegistry"               # Remote Registry
)

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
    
    # Combine with Windows-specific packages
    $allPackages = $WINDOWS_SPECIFIC + $cliPackages + $guiPackages
    
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
    Log-Header "Applying Registry Tweaks (Removing Consumer Bloat)"
    
    foreach ($tweak in $REGISTRY_TWEAKS) {
        $path = $tweak.Path
        $name = $tweak.Name
        $value = $tweak.Value
        $type = $tweak.Type
        
        try {
            # Create path if it doesn't exist
            if (-not (Test-Path $path)) {
                New-Item -Path $path -Force | Out-Null
            }
            
            # Set registry value (handle Binary type specially)
            if ($type -eq "Binary") {
                Set-ItemProperty -Path $path -Name $name -Value $value -Force | Out-Null
            } else {
                Set-ItemProperty -Path $path -Name $name -Value $value -Type $type -Force | Out-Null
            }
            Log-Info "$name set to $value"
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
    
    foreach ($service in $SERVICES_TO_DISABLE) {
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
    Log-Header "Removing Windows Bloatware (Tiny11-Style)"
    
    # Comprehensive bloatware list (based on Tiny11Builder)
    $bloatwareApps = @(
        # Microsoft Apps
        "Microsoft.BingNews"
        "Microsoft.BingWeather"
        "Microsoft.BingFinance"
        "Microsoft.BingSports"
        "Microsoft.GamingApp"
        "Microsoft.GetHelp"
        "Microsoft.Getstarted"
        "Microsoft.MicrosoftSolitaireCollection"
        "Microsoft.MixedReality.Portal"
        "Microsoft.3DBuilder"
        "Microsoft.People"
        "Microsoft.Print3D"
        "Microsoft.WindowsFeedbackHub"
        "Microsoft.WindowsMaps"
        "Microsoft.ZuneMusic"
        "Microsoft.ZuneVideo"
        "Microsoft.YourPhone"
        "Microsoft.Todos"
        "Microsoft.PowerAutomateDesktop"
        "Microsoft.549981C3F5F10"  # Cortana
        "Microsoft.OutlookForWindows"
        "Microsoft.SkypeApp"
        
        # Xbox Apps
        "Microsoft.XboxApp"
        "Microsoft.XboxGameCallableUI"
        "Microsoft.XboxIdentityProvider"
        "Microsoft.XboxSpeechToTextOverlay"
        "Microsoft.XboxGameOverlay"
        "Microsoft.Xbox.TCUI"
        
        # Third-party bloat
        "Clipchamp.Clipchamp"
        "MicrosoftTeams"
        "Microsoft.MicrosoftOfficeHub"
        
        # Optional: uncomment to remove
        # "Microsoft.Windows.Photos"
        # "Microsoft.WindowsCamera"
        # "Microsoft.WindowsCalculator"
    )
    
    foreach ($app in $bloatwareApps) {
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
