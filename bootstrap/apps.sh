#!/bin/bash

echo "Installing Brew packages and MAS apps ..."
{
    awk '/^#/ || !NF {next} /#macos/ || (!/#linux/ && !/#windows/) {print "brew \"" $1 "\""}' bootstrap/config/cli.txt

    awk '/^#/ || !NF {next} /#macos/ || (!/#linux/ && !/#windows/) {print "cask \"" $1 "\""}' bootstrap/config/gui.txt
} | brew bundle --file=-

awk -F'|' '/^[^#]/ && NF>=1 {print $1}' "$(dirname "$0")/config/macos-mas.txt" | xargs mas install

echo "Done."
