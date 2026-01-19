#!/bin/bash
# ============================================================================
# PACMAN/AUR PACKAGE MODULE
# Handles pacman and AUR (yay) packages for Arch Linux
# ============================================================================

# Source libraries if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../../lib"

[[ -z "$LOG_FILE" ]] && source "${LIB_DIR}/logging.sh"
[[ -z "$CONFIG_URL" ]] && source "${LIB_DIR}/config.sh"

# ============================================================================
# PACMAN VERIFICATION
# ============================================================================

# Check if a package is installed via pacman
verify_pacman_installed() {
    local pkg="$1"
    pacman -Qi "$pkg" &>/dev/null
}

# Check if a package exists in official repos
verify_pacman_exists() {
    local pkg="$1"
    pacman -Ss "^${pkg}$" &>/dev/null
}

# Get installed package version
get_pacman_version() {
    local pkg="$1"
    pacman -Qi "$pkg" 2>/dev/null | grep "^Version" | awk '{print $3}'
}

# ============================================================================
# YAY/AUR VERIFICATION
# ============================================================================

# Check if yay is installed
verify_yay_installed() {
    command -v yay &>/dev/null
}

# Check if a package is installed (pacman or AUR)
verify_package_installed() {
    local pkg="$1"
    # yay -Qi checks both pacman and AUR packages
    if verify_yay_installed; then
        yay -Qi "$pkg" &>/dev/null
    else
        pacman -Qi "$pkg" &>/dev/null
    fi
}

# Check if package exists in AUR
verify_aur_exists() {
    local pkg="$1"
    if verify_yay_installed; then
        yay -Ss "^${pkg}$" 2>/dev/null | grep -q "aur/${pkg}"
    else
        return 1
    fi
}

# ============================================================================
# SYSTEM UPDATE
# ============================================================================

# Update system
update_system() {
    log_header "Updating System"

    log_info "Running pacman -Syu..."
    sudo pacman -Syu --noconfirm >> "$LOG_FILE" 2>&1
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "System updated"
        return 0
    else
        log_error "System update failed (exit code: $exit_code)"
        return 1
    fi
}

# ============================================================================
# PACMAN INSTALLATION
# ============================================================================

# Install packages via pacman
install_pacman_packages() {
    log_header "Installing Pacman Packages"

    log_info "Loading packages from config..."

    # Load packages from multiple sources
    local cli_packages
    mapfile -t cli_packages < <(load_packages "cli.txt" "linux")

    local gui_packages
    mapfile -t gui_packages < <(load_packages "gui.txt" "linux")

    local arch_packages
    mapfile -t arch_packages < <(load_config "linux-packages.txt" | grep -v '^#')

    # Combine all packages
    local all_packages=()
    all_packages+=("${arch_packages[@]}")
    all_packages+=("${cli_packages[@]}")
    all_packages+=("${gui_packages[@]}")

    local to_install=()
    local already_installed=0
    local aur_packages=()
    local failed=()

    for pkg in "${all_packages[@]}"; do
        # Skip empty, markers, and comments
        [[ -z "$pkg" ]] && continue
        [[ "$pkg" == "#nvidia" || "$pkg" == "#aur" ]] && continue

        if verify_pacman_installed "$pkg"; then
            log_success "$pkg ($(get_pacman_version "$pkg"))"
            ((already_installed++))
        elif verify_pacman_exists "$pkg"; then
            to_install+=("$pkg")
        else
            # Package not in official repos, will try AUR later
            aur_packages+=("$pkg")
            log_debug "$pkg not in repos (will try AUR)"
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_info "All official repo packages already installed ($already_installed packages)"
    else
        log_info "Installing ${#to_install[@]} packages from official repos..."

        for pkg in "${to_install[@]}"; do
            log_info "Installing $pkg..."
            sudo pacman -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1

            # Verify installation
            if verify_pacman_installed "$pkg"; then
                log_success "$pkg installed ($(get_pacman_version "$pkg"))"
            else
                log_error "$pkg installation failed"
                failed+=("$pkg")
            fi
        done
    fi

    # Store AUR packages for later
    AUR_PENDING=("${aur_packages[@]}")

    # Summary
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Failed to install: ${failed[*]}"
        return 1
    fi

    return 0
}

# ============================================================================
# YAY INSTALLATION
# ============================================================================

# Install yay AUR helper
install_yay() {
    log_header "Installing yay (AUR Helper)"

    if verify_yay_installed; then
        log_success "yay already installed"
        return 0
    fi

    log_info "Building yay from AUR..."

    # Create temp directory
    local temp_dir
    temp_dir=$(mktemp -d)

    # Clone yay
    git clone https://aur.archlinux.org/yay.git "$temp_dir/yay" >> "$LOG_FILE" 2>&1

    if [[ ! -d "$temp_dir/yay" ]]; then
        log_error "Failed to clone yay repository"
        rm -rf "$temp_dir"
        return 1
    fi

    # Build and install
    (
        cd "$temp_dir/yay" || exit 1
        makepkg -si --noconfirm >> "$LOG_FILE" 2>&1
    )

    # Cleanup
    rm -rf "$temp_dir"

    # Verify installation
    if verify_yay_installed; then
        log_success "yay installed"
        return 0
    else
        log_error "yay installation failed"
        return 1
    fi
}

# ============================================================================
# AUR INSTALLATION
# ============================================================================

# Install AUR packages
install_aur_packages() {
    log_header "Installing AUR Packages"

    if ! verify_yay_installed; then
        log_error "yay not available, skipping AUR packages"
        return 1
    fi

    # Load AUR-only packages from config
    local aur_only
    mapfile -t aur_only < <(load_section "linux-packages.txt" "aur")

    # Combine with pending AUR packages from pacman phase
    local all_aur=()
    all_aur+=("${AUR_PENDING[@]}")
    all_aur+=("${aur_only[@]}")

    # Remove duplicates
    local unique_aur=()
    for pkg in "${all_aur[@]}"; do
        [[ -z "$pkg" ]] && continue
        if ! in_array "$pkg" "${unique_aur[@]}"; then
            unique_aur+=("$pkg")
        fi
    done

    if [[ ${#unique_aur[@]} -eq 0 ]]; then
        log_info "No AUR packages to install"
        return 0
    fi

    local to_install=()
    local already_installed=0
    local failed=()

    for pkg in "${unique_aur[@]}"; do
        if verify_package_installed "$pkg"; then
            log_success "$pkg (already installed)"
            ((already_installed++))
        else
            to_install+=("$pkg")
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_info "All AUR packages already installed ($already_installed packages)"
        return 0
    fi

    log_info "Installing ${#to_install[@]} AUR packages..."

    for pkg in "${to_install[@]}"; do
        log_info "Installing $pkg from AUR..."
        yay -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1

        # Verify installation
        if verify_package_installed "$pkg"; then
            log_success "$pkg installed"
        else
            log_error "$pkg installation failed"
            failed+=("$pkg")
        fi
    done

    # Summary
    local installed=$((${#to_install[@]} - ${#failed[@]}))
    if [[ ${#failed[@]} -gt 0 ]]; then
        log_warning "Installed $installed/${#to_install[@]} AUR packages. Failed: ${failed[*]}"
        return 1
    else
        log_success "All AUR packages installed successfully"
        return 0
    fi
}

# ============================================================================
# NVIDIA DRIVERS
# ============================================================================

# Install NVIDIA drivers if GPU detected
install_nvidia() {
    log_header "Installing NVIDIA Driver"

    # Check if NVIDIA GPU present
    if ! lspci | grep -i nvidia &>/dev/null; then
        log_info "No NVIDIA GPU detected, skipping"
        return 0
    fi

    log_info "NVIDIA GPU detected"

    # Load nvidia packages from config
    local nvidia_packages
    mapfile -t nvidia_packages < <(load_section "linux-packages.txt" "nvidia")

    if [[ ${#nvidia_packages[@]} -eq 0 ]]; then
        log_warning "No NVIDIA packages defined in config"
        return 1
    fi

    local failed=()

    for pkg in "${nvidia_packages[@]}"; do
        [[ -z "$pkg" ]] && continue

        if verify_pacman_installed "$pkg"; then
            log_success "$pkg (already installed)"
        else
            log_info "Installing $pkg..."
            sudo pacman -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1

            # Verify installation
            if verify_pacman_installed "$pkg"; then
                log_success "$pkg installed"
            else
                log_error "$pkg installation failed"
                failed+=("$pkg")
            fi
        fi
    done

    # Configure NVIDIA for Wayland
    log_info "Configuring NVIDIA for Wayland..."

    # Kernel parameter
    local modprobe_file="/etc/modprobe.d/nvidia.conf"
    local modprobe_content="options nvidia_drm modeset=1 fbdev=1"

    sudo mkdir -p /etc/modprobe.d
    echo "$modprobe_content" | sudo tee "$modprobe_file" > /dev/null

    # Verify modprobe config
    if [[ -f "$modprobe_file" ]] && grep -q "modeset=1" "$modprobe_file"; then
        log_success "NVIDIA modprobe config created"
    else
        log_error "Failed to create NVIDIA modprobe config"
    fi

    # Environment variables for Sway
    local env_file="/etc/environment.d/nvidia-wayland.conf"
    sudo mkdir -p /etc/environment.d

    cat << 'EOF' | sudo tee "$env_file" > /dev/null
WLR_NO_HARDWARE_CURSORS=1
LIBVA_DRIVER_NAME=nvidia
GBM_BACKEND=nvidia-drm
__GLX_VENDOR_LIBRARY_NAME=nvidia
EOF

    # Verify environment config
    if [[ -f "$env_file" ]] && grep -q "WLR_NO_HARDWARE_CURSORS" "$env_file"; then
        log_success "NVIDIA Wayland environment configured"
    else
        log_error "Failed to create NVIDIA environment config"
    fi

    # Rebuild initramfs
    log_info "Rebuilding initramfs..."
    sudo mkinitcpio -P >> "$LOG_FILE" 2>&1

    if [[ $? -eq 0 ]]; then
        log_success "Initramfs rebuilt"
    else
        log_warning "Initramfs rebuild may have had issues"
    fi

    log_success "NVIDIA configured for Wayland"
    log_warning "Reboot required for NVIDIA changes to take effect"

    if [[ ${#failed[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ============================================================================
# PACKAGE REMOVAL
# ============================================================================

# Remove a specific package
remove_package() {
    local pkg="$1"

    if ! verify_package_installed "$pkg"; then
        log_info "$pkg not installed"
        return 0
    fi

    log_info "Removing $pkg..."
    sudo pacman -Rns --noconfirm "$pkg" >> "$LOG_FILE" 2>&1

    # Verify removal
    if ! verify_package_installed "$pkg"; then
        log_success "$pkg removed"
        return 0
    else
        log_error "$pkg removal failed"
        return 1
    fi
}

# ============================================================================
# CLEANUP
# ============================================================================

# Clean package cache and orphans
cleanup_pacman() {
    log_header "Cleaning up Pacman"

    # Remove orphaned packages
    log_info "Checking for orphaned packages..."
    local orphans
    orphans=$(pacman -Qtdq 2>/dev/null)

    if [[ -n "$orphans" ]]; then
        log_info "Removing orphaned packages..."
        echo "$orphans" | sudo pacman -Rns --noconfirm - >> "$LOG_FILE" 2>&1

        # Verify orphans removed
        local remaining_orphans
        remaining_orphans=$(pacman -Qtdq 2>/dev/null)
        if [[ -z "$remaining_orphans" ]]; then
            log_success "Orphaned packages removed"
        else
            log_warning "Some orphans could not be removed"
        fi
    else
        log_success "No orphaned packages found"
    fi

    # Clean package cache
    log_info "Cleaning package cache..."
    sudo pacman -Sc --noconfirm >> "$LOG_FILE" 2>&1

    log_success "Pacman cleanup complete"
}

# ============================================================================
# STATUS
# ============================================================================

# Show package status
get_pacman_status() {
    log_header "Package Status"

    # Count installed packages
    local total_packages
    total_packages=$(pacman -Q | wc -l)
    log_info "Total installed packages: $total_packages"

    # Check for updates
    log_info "Checking for updates..."
    local updates
    updates=$(pacman -Qu 2>/dev/null | wc -l)

    if [[ $updates -eq 0 ]]; then
        log_success "All packages are up to date"
    else
        log_warning "$updates packages have updates available"
    fi

    # Check for orphans
    local orphans
    orphans=$(pacman -Qtdq 2>/dev/null | wc -l)

    if [[ $orphans -eq 0 ]]; then
        log_success "No orphaned packages"
    else
        log_warning "$orphans orphaned packages found"
    fi
}

# Global variable for pending AUR packages
AUR_PENDING=()
