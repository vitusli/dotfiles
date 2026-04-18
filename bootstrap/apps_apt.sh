#!/bin/bash
set -euo pipefail

PKGS=$(awk '/^#/||!NF{next}{print $1}' "$(dirname "$0")/config/apt.txt")

sudo apt-get update
sudo apt-get install -y $PKGS
