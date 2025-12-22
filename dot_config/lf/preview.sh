#!/bin/sh

# Preview script for lf file manager
# Uses bat for text files, shows file info for others

case "$1" in
    *.tar*) tar tf "$1";;
    *.zip) unzip -l "$1";;
    *.rar) unrar l "$1";;
    *.7z) 7z l "$1";;
    *.pdf) pdftotext "$1" -;;
    *) 
        if command -v bat &> /dev/null; then
            bat --color=always --style=numbers "$1" 2>/dev/null || file -b "$1"
        else
            cat "$1" 2>/dev/null || file -b "$1"
        fi
    ;;
esac
