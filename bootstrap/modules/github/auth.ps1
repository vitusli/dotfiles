# ============================================================================
# GITHUB AUTHENTICATION MODULE
# Handles GitHub CLI auth and SSH key setup for Windows
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Info -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}

# ============================================================================
# GITHUB CLI VERIFICATION
# ============================================================================

# Check if GitHub CLI is installed
function Verify-GHInstalled
{
    $null = Get-Command gh -ErrorAction SilentlyContinue
    return $?
}

# Check if GitHub CLI is authenticated
function Verify-GHAuthenticated
{
    if (-not (Verify-GHInstalled))
    {
        return $false
    }
    $null = & gh auth status 2>&1
    return $?
}

# Get authenticated GitHub username
function Get-GHUsername
{
    if (Verify-GHAuthenticated)
    {
        return & gh api user --jq '.login' 2>$null
    }
    return $null
}

# ============================================================================
# SSH KEY VERIFICATION
# ============================================================================

# Check if SSH key exists
function Verify-SSHKeyExists
{
    param(
        [string]$KeyPath = "$HOME\.ssh\id_ed25519"
    )
    return Test-Path $KeyPath
}

# Get SSH key fingerprint
function Get-SSHFingerprint
{
    param(
        [string]$KeyPath = "$HOME\.ssh\id_ed25519.pub"
    )
    if (Test-Path $KeyPath)
    {
        $output = ssh-keygen -lf $KeyPath 2>$null
        if ($output)
        {
            return ($output -split ' ')[1]
        }
    }
    return $null
}

# Check if SSH key is on GitHub
function Verify-SSHKeyOnGitHub
{
    param(
        [string]$KeyPath = "$HOME\.ssh\id_ed25519.pub"
    )

    if (-not (Verify-GHAuthenticated))
    {
        return $false
    }

    $fingerprint = Get-SSHFingerprint -KeyPath $KeyPath
    if (-not $fingerprint)
    {
        return $false
    }

    $existingKeys = & gh ssh-key list 2>$null
    return ($existingKeys -match [regex]::Escape($fingerprint))
}

# ============================================================================
# GITHUB CLI AUTHENTICATION
# ============================================================================

# Authenticate with GitHub CLI
function Setup-GitHubAuth
{
    Log-Header "Setting up GitHub Authentication"

    if (-not (Verify-GHInstalled))
    {
        Log-Error "GitHub CLI (gh) not found. Install it first."
        return $false
    }

    if (Verify-GHAuthenticated)
    {
        $username = Get-GHUsername
        Log-Success "GitHub CLI already authenticated as '$username'"
        return $true
    }

    Log-Info "Authenticating with GitHub CLI..."
    & gh auth login --scopes repo --web

    # Verify authentication
    if (Verify-GHAuthenticated)
    {
        $username = Get-GHUsername
        Log-Success "GitHub CLI authenticated as '$username'"
        return $true
    } else
    {
        Log-Error "GitHub CLI authentication failed"
        return $false
    }
}

# ============================================================================
# SSH KEY SETUP
# ============================================================================

# Generate SSH key if it doesn't exist
function Setup-SSHKey
{
    Log-Header "Setting up SSH Key"

    $sshKey = "$HOME\.ssh\id_ed25519"
    $sshPub = "$sshKey.pub"

    # Check if key already exists
    if (Verify-SSHKeyExists -KeyPath $sshKey)
    {
        $fingerprint = Get-SSHFingerprint -KeyPath $sshPub
        Log-Success "SSH key already exists (fingerprint: $fingerprint)"
    } else
    {
        Log-Info "Generating SSH key..."

        # Create .ssh directory
        $sshDir = "$HOME\.ssh"
        if (-not (Test-Path $sshDir))
        {
            New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
        }

        # Determine email for key
        $sshEmail = git config --global user.email 2>$null
        if (-not $sshEmail)
        {
            $sshEmail = "user@$env:COMPUTERNAME"
            Log-Info "Using default email: $sshEmail"
        } else
        {
            Log-Info "Using git email: $sshEmail"
        }

        # Generate key
        ssh-keygen -t ed25519 -C $sshEmail -f $sshKey -N '""' | Out-Null

        # Verify key was created
        if (Verify-SSHKeyExists -KeyPath $sshKey)
        {
            $fingerprint = Get-SSHFingerprint -KeyPath $sshPub
            Log-Success "SSH key generated (fingerprint: $fingerprint)"
        } else
        {
            Log-Error "SSH key generation failed"
            return $false
        }
    }

    # Start SSH agent and add key (Windows specific)
    try
    {
        $sshAgentService = Get-Service ssh-agent -ErrorAction SilentlyContinue
        if ($sshAgentService)
        {
            if ($sshAgentService.Status -ne 'Running')
            {
                Log-Info "Starting SSH agent service..."
                Start-Service ssh-agent -ErrorAction SilentlyContinue
            }

            Log-Info "Adding SSH key to SSH agent..."
            ssh-add $sshKey 2>$null

            if ($?)
            {
                Log-Success "SSH key added to SSH agent"
            } else
            {
                Log-Warning "Could not add SSH key to agent"
            }
        }
    } catch
    {
        Log-Warning "Could not configure SSH agent: $_"
    }

    return $true
}

# Add SSH key to GitHub
function Add-SSHKeyToGitHub
{
    param(
        [string]$KeyTitle = "$env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd')"
    )

    $sshPub = "$HOME\.ssh\id_ed25519.pub"
    $sshKey = "$HOME\.ssh\id_ed25519"

    if (-not (Verify-SSHKeyExists -KeyPath $sshKey))
    {
        Log-Error "SSH key does not exist"
        return $false
    }

    if (-not (Verify-GHAuthenticated))
    {
        Log-Warning "GitHub CLI not authenticated, cannot add SSH key automatically"
        Log-Info "Add your SSH key manually at: https://github.com/settings/keys"
        Write-Output ""
        Get-Content $sshPub
        Write-Output ""
        return $false
    }

    # Check if key is already on GitHub
    if (Verify-SSHKeyOnGitHub -KeyPath $sshPub)
    {
        Log-Success "SSH key already on GitHub"
        return $true
    }

    Log-Info "Adding SSH key to GitHub..."
    & gh ssh-key add $sshPub --title $KeyTitle 2>$null

    if ($?)
    {
        # Verify key was added
        if (Verify-SSHKeyOnGitHub -KeyPath $sshPub)
        {
            Log-Success "SSH key added to GitHub"
            return $true
        } else
        {
            Log-Error "SSH key add command succeeded but key not found on GitHub"
            return $false
        }
    } else
    {
        Log-Error "Failed to add SSH key to GitHub"
        Log-Info "Add manually at: https://github.com/settings/keys"
        Write-Output ""
        Get-Content $sshPub
        Write-Output ""
        return $false
    }
}

# ============================================================================
# GIT CONFIGURATION
# ============================================================================

# Verify git user is configured
function Verify-GitConfigured
{
    $email = git config --global user.email 2>$null
    $name = git config --global user.name 2>$null
    return ($email -and $name)
}

# Setup git configuration
function Setup-GitConfig
{
    Log-Header "Setting up Git Configuration"

    if (Verify-GitConfigured)
    {
        $name = git config --global user.name
        $email = git config --global user.email
        Log-Success "Git already configured: $name <$email>"
        return $true
    }

    Log-Info "Configuring git..."

    # Try to get info from GitHub CLI if authenticated
    if (Verify-GHAuthenticated)
    {
        $ghName = & gh api user --jq '.name' 2>$null
        $ghEmail = & gh api user/emails --jq '.[0].email' 2>$null

        if ($ghName -and $ghEmail)
        {
            Log-Info "Using GitHub account info: $ghName <$ghEmail>"
            git config --global user.name $ghName
            git config --global user.email $ghEmail

            if (Verify-GitConfigured)
            {
                Log-Success "Git configured from GitHub account"
                return $true
            }
        }
    }

    # Fall back to prompting
    $gitEmail = Read-Host "Enter your Git email"
    $gitName = Read-Host "Enter your Git name"

    git config --global user.email $gitEmail
    git config --global user.name $gitName

    if (Verify-GitConfigured)
    {
        Log-Success "Git configured: $gitName <$gitEmail>"
        return $true
    } else
    {
        Log-Error "Failed to configure git"
        return $false
    }
}

# ============================================================================
# REPOSITORY CLONING
# ============================================================================

# Clone a repository
function Clone-Repo
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Repo,

        [Parameter(Mandatory=$true)]
        [string]$Dest
    )

    $repoName = $Repo.Split('/')[-1]
    $fullPath = Join-Path $Dest $repoName

    # Check if already cloned
    if (Test-Path (Join-Path $fullPath ".git"))
    {
        Log-Success "$repoName (already cloned)"
        return $true
    }

    Log-Info "Cloning $repoName to $Dest..."

    # Create destination directory
    if (-not (Test-Path $Dest))
    {
        New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    }

    # Clone
    if (Verify-GHAuthenticated)
    {
        & gh repo clone $Repo $fullPath 2>$null
    } else
    {
        git clone "https://github.com/$Repo.git" $fullPath 2>$null
    }

    # Verify clone
    if (Test-Path (Join-Path $fullPath ".git"))
    {
        Log-Success "$repoName cloned"
        return $true
    } else
    {
        Log-Error "Failed to clone $repoName"
        return $false
    }
}

# Clone repositories from config
function Clone-Repositories
{
    Log-Header "Cloning GitHub Repositories"

    if (-not (Get-Command git -ErrorAction SilentlyContinue))
    {
        Log-Error "Git not installed"
        return $false
    }

    Log-Info "Loading repositories from config..."

    # Load config if function exists
    $repos = @()
    if (Get-Command Load-Config -ErrorAction SilentlyContinue)
    {
        $repos = Load-Config "repos.txt"
    }

    if (-not $repos -or $repos.Count -eq 0)
    {
        Log-Info "No repositories defined in config"
        return $true
    }

    $failed = @()

    foreach ($repoLine in $repos)
    {
        if (-not $repoLine -or $repoLine.StartsWith('#'))
        {
            continue
        }

        $parts = $repoLine -split '\|'
        $repo = $parts[0]
        $repoPath = $parts[1]

        # Expand variables like $HOME and $DOCUMENTS
        $repoPath = $repoPath -replace '\$HOME', $HOME
        $repoPath = $repoPath -replace '\$DOCUMENTS', "$HOME\Documents"
        $repoPath = [Environment]::ExpandEnvironmentVariables($repoPath)

        if (-not (Clone-Repo -Repo $repo -Dest $repoPath))
        {
            $failed += $repo
        }
    }

    if ($failed.Count -gt 0)
    {
        Log-Warning "Failed to clone: $($failed -join ', ')"
        return $false
    }

    Log-Success "All repositories cloned"
    return $true
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full GitHub setup
function Setup-GitHub
{
    $errors = 0

    if (-not (Setup-GitConfig))
    { $errors++ 
    }
    if (-not (Setup-GitHubAuth))
    { $errors++ 
    }
    if (-not (Setup-SSHKey))
    { $errors++ 
    }
    if (-not (Add-SSHKeyToGitHub -KeyTitle "$env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd')"))
    { $errors++ 
    }

    if ($errors -gt 0)
    {
        Log-Warning "GitHub setup completed with $errors issues"
        return $false
    }

    Log-Success "GitHub setup complete"
    return $true
}
