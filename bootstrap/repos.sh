#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config/repos.txt"

if ! command -v gh >/dev/null 2>&1; then
    echo "Skipping repos: gh is not installed yet."
    exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "Skipping repos: gh is not authenticated yet (run: gh auth login)."
    exit 0
fi

active_tags=()
if [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    active_tags=("wsl" "linux")
elif [[ "$(uname -s)" == "Darwin" ]]; then
    active_tags=("macos")
elif [[ "$(uname -s)" == "Linux" ]]; then
    active_tags=("linux")
fi

has_matching_tag() {
    local line="$1"
    local line_tags=()
    local tag

    while IFS= read -r tag; do
        [[ -n "$tag" ]] && line_tags+=("$tag")
    done < <(printf '%s\n' "$line" | grep -oE '#[A-Za-z0-9_-]+' | sed 's/^#//' || true)

    if [[ ${#line_tags[@]} -eq 0 ]]; then
        return 0
    fi

    for tag in "${line_tags[@]}"; do
        for active in "${active_tags[@]}"; do
            [[ "$tag" == "$active" ]] && return 0
        done
    done

    return 1
}

echo "Cloning repositories..."
while IFS= read -r line; do
    line="${line%%$'\r'}"
    [[ -z "${line//[[:space:]]/}" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    has_matching_tag "$line" || continue

    data_part="${line%%#*}"
    [[ -z "${data_part//[[:space:]]/}" ]] && continue

    IFS='|' read -r repo dest <<< "$data_part"
    repo="$(echo "$repo" | xargs)"
    dest="$(echo "$dest" | xargs)"
    [[ -z "$repo" || -z "$dest" ]] && continue

    parent="${dest/#\~/$HOME}"
    target="$parent/${repo##*/}"

    if [[ -d "$target" ]]; then
        echo "Skipping existing repo: $repo"
        continue
    fi

    mkdir -p "$parent"
    gh repo clone "$repo" "$target"
done < "$CONFIG_FILE"
echo "Done."
