#!/bin/bash
set -euo pipefail
brew >/dev/null
{ awk '/^#/||!NF{next}/#brew/{print "brew \""$1"\""}' "$(dirname "$0")/config/cli.txt" | { [[ "$(uname -s)" == "Linux" ]] && grep -Ev '^brew "git"$' || cat; }; [[ "$(uname -s)" == "Darwin" ]] && awk '/^#/||!NF{next}/#brew/{print "cask \""$1"\""}' "$(dirname "$0")/config/gui.txt"; } | brew bundle --file=-

# git blacklisted on linux
