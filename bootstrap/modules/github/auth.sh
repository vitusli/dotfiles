#!/bin/bash
# ============================================================================
# GITHUB AUTHENTICATION MODULE
# Handles GitHub CLI auth and SSH key setup for macOS/Linux
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"

# ============================================================================
# GITHUB CLI VERIFICATION
# ============================================================================

# Check if GitHub CLI is installed
verify_gh_installed() {
    command -v gh &>/dev/null
}

# Check if GitHub CLI is authenticated
verify_gh_authenticated() {
    if ! verify_gh_installed; then
        return 1
    fi
    gh auth status &>/dev/null 2>&1
}

# Get authenticated GitHub username
get_gh_username() {
    if verify_gh_authenticated; then
        gh api user --jq '.login' 2>/dev/null
    fi
}

# ============================================================================
# SSH KEY VERIFICATION
# ============================================================================

# Check if SSH key exists
verify_ssh_key_exists() {
    local key_path="${1:-$HOME/.ssh/id_ed25519}"
    [[ -f "$key_path" ]]
}

# Get SSH key fingerprint
get_ssh_fingerprint() {
    local key_path="${1:-$HOME/.ssh/id_ed25519.pub}"
    if [[ -f "$key_path" ]]; then
        ssh-keygen -lf "$key_path" 2>/dev/null | awk '{print $2}'
    fi
}

# Check if SSH key is on GitHub
verify_ssh_key_on_github() {
    local key_path="${1:-$HOME/.ssh/id_ed25519.pub}"

    if ! verify_gh_authenticated; then
        return 1
    fi

    local fingerprint
    fingerprint=$(get_ssh_fingerprint "$key_path")

    if [[ -z "$fingerprint" ]]; then
        return 1
    fi

    gh ssh-key list 2>/dev/null | grep -q "$fingerprint"
}

# ============================================================================
# GITHUB CLI AUTHENTICATION
# ============================================================================

# Authenticate with GitHub CLI
setup_github_auth() {
    log_header "Setting up GitHub Authentication"

    if ! verify_gh_installed; then
        log_error "GitHub CLI (gh) not found. Install it first."
        return 1
    fi

    if verify_gh_authenticated; then
        local username
        username=$(get_gh_username)
        log_success "GitHub CLI already authenticated as '$username'"
        return 0
    fi

    log_info "Authenticating with GitHub CLI..."
    gh auth login --scopes repo --web

    # Verify authentication
    if verify_gh_authenticated; then
        local username
        username=$(get_gh_username)
        log_success "GitHub CLI authenticated as '$username'"
        return 0
    else
        log_error "GitHub CLI authentication failed"
        return 1
    fi
}

# ============================================================================
# SSH KEY SETUP
# ============================================================================

# Generate SSH key if it doesn't exist
setup_ssh_key() {
    log_header "Setting up SSH Key"

    local ssh_key="$HOME/.ssh/id_ed25519"
    local ssh_pub="${ssh_key}.pub"

    # Check if key already exists
    if verify_ssh_key_exists "$ssh_key"; then
        local fingerprint
        fingerprint=$(get_ssh_fingerprint "$ssh_pub")
        log_success "SSH key already exists (fingerprint: $fingerprint)"
    else
        log_info "Generating SSH key..."

        # Create .ssh directory with correct permissions
        mkdir -p "$HOME/.ssh"
        chmod 700 "$HOME/.ssh"

        # Determine email for key
        local ssh_email
        if git config --global user.email &>/dev/null; then
            ssh_email=$(git config --global user.email)
            log_info "Using git email: $ssh_email"
        else
            ssh_email="user@$(hostname)"
            log_info "Using default email: $ssh_email"
        fi

        # Generate key
        ssh-keygen -t ed25519 -C "$ssh_email" -f "$ssh_key" -N ""

        # Set correct permissions
        chmod 600 "$ssh_key"
        chmod 644 "$ssh_pub"

        # Verify key was created
        if verify_ssh_key_exists "$ssh_key"; then
            local fingerprint
            fingerprint=$(get_ssh_fingerprint "$ssh_pub")
            log_success "SSH key generated (fingerprint: $fingerprint)"
        else
            log_error "SSH key generation failed"
            return 1
        fi
    fi

    # Add to SSH agent (macOS specific)
    if [[ "$(detect_os)" == "macos" ]]; then
        log_info "Adding SSH key to macOS keychain..."
        eval "$(ssh-agent -s)" &>/dev/null
        ssh-add --apple-use-keychain "$ssh_key" &>/dev/null

        # Verify key was added to agent
        if ssh-add -l 2>/dev/null | grep -q "$(get_ssh_fingerprint "$ssh_pub")"; then
            log_success "SSH key added to macOS keychain"
        else
            log_warning "Could not add SSH key to keychain"
        fi
    fi

    return 0
}

# Add SSH key to GitHub
add_ssh_key_to_github() {
    local ssh_pub="$HOME/.ssh/id_ed25519.pub"
    local key_title="${1:-$(hostname)}"

    if ! verify_ssh_key_exists "${ssh_pub%.pub}"; then
        log_error "SSH key does not exist"
        return 1
    fi

    if ! verify_gh_authenticated; then
        log_warning "GitHub CLI not authenticated, cannot add SSH key automatically"
        log_info "Add your SSH key manually at: https://github.com/settings/keys"
        echo ""
        cat "$ssh_pub"
        echo ""
        return 1
    fi

    # Check if key is already on GitHub
    if verify_ssh_key_on_github "$ssh_pub"; then
        log_success "SSH key already on GitHub"
        return 0
    fi

    log_info "Adding SSH key to GitHub..."
    if gh ssh-key add "$ssh_pub" --title "$key_title" 2>> "$LOG_FILE"; then
        # Verify key was added
        if verify_ssh_key_on_github "$ssh_pub"; then
            log_success "SSH key added to GitHub"
            return 0
        else
            log_error "SSH key add command succeeded but key not found on GitHub"
            return 1
        fi
    else
        log_error "Failed to add SSH key to GitHub"
        log_info "Add manually at: https://github.com/settings/keys"
        echo ""
        cat "$ssh_pub"
        echo ""
        return 1
    fi
}

# ============================================================================
# GIT CONFIGURATION
# ============================================================================

# Verify git user is configured
verify_git_configured() {
    git config --global user.email &>/dev/null && git config --global user.name &>/dev/null
}

# Setup git configuration
setup_git_config() {
    log_header "Setting up Git Configuration"

    if verify_git_configured; then
        local name email
        name=$(git config --global user.name)
        email=$(git config --global user.email)
        log_success "Git already configured: $name <$email>"
        return 0
    fi

    log_info "Configuring git..."

    # Try to get info from GitHub CLI if authenticated
    if verify_gh_authenticated; then
        local gh_name gh_email
        gh_name=$(gh api user --jq '.name' 2>/dev/null)
        gh_email=$(gh api user/emails --jq '.[0].email' 2>/dev/null)

        if [[ -n "$gh_name" && -n "$gh_email" ]]; then
            log_info "Using GitHub account info: $gh_name <$gh_email>"
            git config --global user.name "$gh_name"
            git config --global user.email "$gh_email"

            if verify_git_configured; then
                log_success "Git configured from GitHub account"
                return 0
            fi
        fi
    fi

    # Fall back to prompting
    read -r -p "Enter your Git email: " git_email
    read -r -p "Enter your Git name: " git_name

    git config --global user.email "$git_email"
    git config --global user.name "$git_name"

    if verify_git_configured; then
        log_success "Git configured: $git_name <$git_email>"
        return 0
    else
        log_error "Failed to configure git"
        return 1
    fi
}

# ============================================================================
# REPOSITORY CLONING
# ============================================================================

# Clone a repository
clone_repo() {
    local repo="$1"      # e.g., "user/repo" or full URL
    local dest="$2"      # destination directory

    if [[ -z "$repo" || -z "$dest" ]]; then
        log_error "clone_repo requires repo and destination"
        return 1
    fi

    local repo_name="${repo##*/}"
    local full_path="$dest/$repo_name"

    # Check if already cloned
    if [[ -d "$full_path/.git" ]]; then
        log_success "$repo_name (already cloned)"
        return 0
    fi

    log_info "Cloning $repo_name to $dest..."

    # Create destination directory
    mkdir -p "$dest"

    # Clone
    if verify_gh_authenticated; then
        gh repo clone "$repo" "$full_path" >> "$LOG_FILE" 2>&1
    else
        git clone "https://github.com/${repo}.git" "$full_path" >> "$LOG_FILE" 2>&1
    fi

    # Verify clone
    if [[ -d "$full_path/.git" ]]; then
        log_success "$repo_name cloned"
        return 0
    else
        log_error "Failed to clone $repo_name"
        return 1
    fi
}

# Clone repositories from config
clone_repositories() {
    log_header "Cloning GitHub Repositories"

    if ! verify_command git; then
        log_error "Git not installed"
        return 1
    fi

    log_info "Loading repositories from config..."

    local repos=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && repos+=("$line")
    done < <(load_config "repos.txt")

    if [[ ${#repos[@]} -eq 0 ]]; then
        log_info "No repositories defined in config"
        return 0
    fi

    local failed=()

    for repo_info in "${repos[@]}"; do
        local repo="${repo_info%%|*}"
        local repo_path="${repo_info#*|}"

        # Expand variables like $HOME and $DOCUMENTS
        repo_path=$(eval echo "$repo_path")

        if ! clone_repo "$repo" "$repo_path"; then
            failed+=("$repo")
        fi
    done

    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Failed to clone: ${failed[*]}"
        return 1
    fi

    log_success "All repositories cloned"
    return 0
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full GitHub setup
setup_github() {
    local errors=0

    setup_git_config || ((errors++))
    setup_github_auth || ((errors++))
    setup_ssh_key || ((errors++))
    add_ssh_key_to_github "$(hostname) $(date +%Y-%m-%d)" || ((errors++))

    if [[ $errors -gt 0 ]]; then
        log_warning "GitHub setup completed with $errors issues"
        return 1
    fi

    log_success "GitHub setup complete"
    return 0
}
