#!/bin/bash
echo "Cloning repositories..."
while IFS='|' read -r r d; do
    [[ -n "$r" && "$r" != \#* ]] && gh repo clone "$r" "${d/\~/$HOME}/${r##*/}"
done < "$(dirname "$0")/config/repos.txt"
echo "Done."
