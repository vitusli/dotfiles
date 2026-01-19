#!/bin/bash
# ============================================================================
# LOGGING LIBRARY
# Shared logging functions for all bash bootstrap scripts
# ============================================================================

# Colors (only if terminal supports it)
if [[ -t 1 ]] && [[ -n "$TERM" ]] && command -v tput &>/dev/null; then
    COLOR_RED=$(tput setaf 1)
    COLOR_GREEN=$(tput setaf 2)
    COLOR_YELLOW=$(tput setaf 3)
    COLOR_BLUE=$(tput setaf 4)
    COLOR_RESET=$(tput sgr0)
else
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_YELLOW=""
    COLOR_BLUE=""
    COLOR_RESET=""
fi

# Log file (can be overridden by sourcing script)
LOG_FILE="${LOG_FILE:-/tmp/bootstrap-$(date +%Y%m%d-%H%M%S).log}"

# ============================================================================
# CORE LOGGING FUNCTIONS
# ============================================================================

log_header() {
    local msg="$1"
    local output=""
    output+="\n════════════════════════════════════════════════════════════\n"
    output+="▶ ${msg}\n"
    output+="════════════════════════════════════════════════════════════"

    echo -e "${COLOR_BLUE}${output}${COLOR_RESET}"
    echo -e "$output" >> "$LOG_FILE"
}

log_success() {
    local msg="✓ $1"
    echo -e "${COLOR_GREEN}${msg}${COLOR_RESET}"
    echo "$msg" >> "$LOG_FILE"
}

log_info() {
    local msg="ℹ $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE"
}

log_warning() {
    local msg="⚠ $1"
    echo -e "${COLOR_YELLOW}${msg}${COLOR_RESET}"
    echo "$msg" >> "$LOG_FILE"
}

log_error() {
    local msg="✗ $1"
    echo -e "${COLOR_RED}${msg}${COLOR_RESET}"
    echo "$msg" >> "$LOG_FILE"
}

log_debug() {
    local msg="  → $1"
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${COLOR_BLUE}${msg}${COLOR_RESET}"
    fi
    echo "$msg" >> "$LOG_FILE"
}

# ============================================================================
# VERIFICATION HELPERS
# These functions perform actual verification instead of trusting exit codes
# ============================================================================

# Verify a command exists
# Usage: verify_command "git" && log_success "git available"
verify_command() {
    local cmd="$1"
    command -v "$cmd" &>/dev/null
}

# Verify a file exists
# Usage: verify_file "$HOME/.zshrc" && log_success ".zshrc exists"
verify_file() {
    local path="$1"
    [[ -f "$path" ]]
}

# Verify a directory exists
# Usage: verify_dir "$HOME/.config" && log_success ".config exists"
verify_dir() {
    local path="$1"
    [[ -d "$path" ]]
}

# Verify a symlink exists and points to expected target
# Usage: verify_symlink "/usr/local/bin/marta" "/Applications/Marta.app/..."
verify_symlink() {
    local link="$1"
    local expected_target="$2"

    if [[ -L "$link" ]]; then
        if [[ -n "$expected_target" ]]; then
            [[ "$(readlink "$link")" == "$expected_target" ]]
        else
            return 0
        fi
    else
        return 1
    fi
}

# Verify a string is in a file
# Usage: verify_in_file "/etc/passwd" "zsh$"
verify_in_file() {
    local file="$1"
    local pattern="$2"
    grep -q "$pattern" "$file" 2>/dev/null
}

# Verify environment variable is set
# Usage: verify_env "EDITOR"
verify_env() {
    local var="$1"
    [[ -n "${!var}" ]]
}

# ============================================================================
# PLATFORM DETECTION
# ============================================================================

detect_os() {
    case "$(uname -s)" in
        Darwin*)  echo "macos" ;;
        Linux*)   echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        *)             echo "unknown" ;;
    esac
}

# ============================================================================
# EXECUTION HELPERS
# ============================================================================

# Run a command and verify its result with a custom check
# Usage: run_and_verify "Installing git" "sudo pacman -S git" "verify_command git"
run_and_verify() {
    local description="$1"
    local command="$2"
    local verify_cmd="$3"

    log_info "$description..."

    # Run the command, capture output
    local output
    output=$(eval "$command" 2>&1)
    local exit_code=$?

    # Log command output
    echo "Command: $command" >> "$LOG_FILE"
    echo "Exit code: $exit_code" >> "$LOG_FILE"
    echo "Output: $output" >> "$LOG_FILE"

    # Verify with custom check if provided
    if [[ -n "$verify_cmd" ]]; then
        if eval "$verify_cmd"; then
            log_success "$description"
            return 0
        else
            log_error "$description - verification failed"
            log_debug "Verification command: $verify_cmd"
            return 1
        fi
    elif [[ $exit_code -eq 0 ]]; then
        log_success "$description"
        return 0
    else
        log_error "$description - command failed (exit code: $exit_code)"
        return 1
    fi
}

# Run a command silently, only log on error
# Usage: run_silent "git pull"
run_silent() {
    local command="$1"
    local output
    output=$(eval "$command" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "Command failed: $command" >> "$LOG_FILE"
        echo "Output: $output" >> "$LOG_FILE"
    fi

    return $exit_code
}

# ============================================================================
# INITIALIZATION
# ============================================================================

init_logging() {
    local log_dir
    log_dir="$(dirname "$LOG_FILE")"

    mkdir -p "$log_dir"

    {
        echo "════════════════════════════════════════════════════════════"
        echo "Bootstrap Log"
        echo "════════════════════════════════════════════════════════════"
        echo "Start Time: $(date)"
        echo "OS: $(detect_os)"
        echo "Arch: $(detect_arch)"
        echo "User: $(whoami)"
        echo "Host: $(hostname)"
        echo "Shell: $SHELL"
        echo "════════════════════════════════════════════════════════════"
        echo ""
    } >> "$LOG_FILE"

    log_info "Log file: $LOG_FILE"
}
