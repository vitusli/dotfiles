#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAS_CONFIG="$SCRIPT_DIR/config/macos-mas.txt"

awk -F'|' '/^[^#]/ && NF>=1 {print $1}' "$MAS_CONFIG" | xargs -n1 mas install
