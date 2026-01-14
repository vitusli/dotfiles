#!/bin/bash

# Configure git filter to convert plist files to XML format when staging
git config --global filter.plist2xml.clean "plutil -convert xml1 -o - -"
git config --global filter.plist2xml.smudge "cat"
