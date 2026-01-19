#!/bin/bash
# ============================================================================
# CONFIG LOADING LIBRARY
# Shared config loading functions for all bash bootstrap scripts
# ============================================================================

# Config URL (can be overridden)
CONFIG_URL="${CONFIG_URL:-https://raw.githubusercontent.com/vitusli/dotfiles/main/config}"
CONFIG_DIR="${CONFIG_DIR:-}"

# ============================================================================
# RAW LOADING
# ============================================================================

# Load raw content from local file or remote URL (fallback)
# Usage: load_raw "cli.txt"
load_raw() {
    local file="$1"

    if [[ -n "$CONFIG_DIR" ]] && [[ -f "${CONFIG_DIR}/${file}" ]]; then
        cat "${CONFIG_DIR}/${file}"
    else
        curl -fsSL "${CONFIG_URL}/${file}" 2>/dev/null
    fi
}

# ============================================================================
# PACKAGE LOADING
# ============================================================================

# Load packages for a specific platform
# Filters out packages tagged for other platforms
# Usage: load_packages "cli.txt" "macos"
# Usage: load_packages "cli.txt" "linux"
# Usage: load_packages "cli.txt" "windows"
load_packages() {
    local file="$1"
    local platform="$2"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$' | \
        awk -v p="#${platform}" '
            # Include if no platform tag at all
            !/#/ { print; next }
            # Include if has our platform tag
            $0 ~ p { print; next }
            # Skip if has other platform tags but not ours
        ' | \
        _filter_other_platforms "$platform" | \
        sed 's/ *#.*//'
}

# Internal helper to filter out lines with other platform tags
_filter_other_platforms() {
    local platform="$1"
    local other_platforms=()

    case "$platform" in
        macos)   other_platforms=("linux" "windows") ;;
        linux)   other_platforms=("macos" "windows") ;;
        windows) other_platforms=("macos" "linux") ;;
    esac

    local line
    while IFS= read -r line; do
        local skip=false
        for other in "${other_platforms[@]}"; do
            if echo "$line" | grep -q "#${other}" && ! echo "$line" | grep -q "#${platform}"; then
                skip=true
                break
            fi
        done
        if [[ "$skip" == "false" ]]; then
            echo "$line"
        fi
    done
}

# Load all packages without platform filtering (strips comments)
# Usage: load_all "vscode.txt"
load_all() {
    local file="$1"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$' | \
        sed 's/ *#.*//'
}

# Load config preserving format (for repos, mas, duti, etc.)
# Only strips comment lines, keeps inline format
# Usage: load_config "repos.txt"
load_config() {
    local file="$1"

    load_raw "$file" | \
        grep -v '^#' | \
        grep -v '^$'
}

# ============================================================================
# SECTION LOADING
# ============================================================================

# Load packages from a specific section in a file
# Sections are marked with #sectionname
# Usage: load_section "linux-packages.txt" "nvidia"
load_section() {
    local file="$1"
    local section="$2"

    load_raw "$file" | \
        sed -n "/#${section}/,/^#[^${section:0:1}]/p" | \
        grep -v "^#" | \
        grep -v '^$'
}

# ============================================================================
# CONFIG PARSING
# ============================================================================

# Parse a pipe-delimited config line
# Usage: parse_config_line "app_id|app_name|extra" 1  # returns app_id
# Usage: parse_config_line "app_id|app_name|extra" 2  # returns app_name
parse_config_field() {
    local line="$1"
    local field="$2"

    echo "$line" | cut -d'|' -f"$field"
}

# Parse config line into array
# Usage: IFS='|' read -ra parts <<< "$(parse_config_line "a|b|c")"
parse_config_line() {
    local line="$1"
    echo "$line"
}

# ============================================================================
# ARRAY HELPERS
# ============================================================================

# Check if item is in array
# Usage: in_array "item" "${array[@]}" && echo "found"
in_array() {
    local item="$1"
    shift
    local arr=("$@")

    for element in "${arr[@]}"; do
        [[ "$element" == "$item" ]] && return 0
    done
    return 1
}

# Read config file into array (one item per line)
# Usage: mapfile -t my_array < <(config_to_array "cli.txt" "macos")
config_to_array() {
    local file="$1"
    local platform="$2"

    if [[ -n "$platform" ]]; then
        load_packages "$file" "$platform"
    else
        load_all "$file"
    fi
}
