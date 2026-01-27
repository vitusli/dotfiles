bootstrap/ssh_setup.sh
#!/bin/bash
echo "Setting up SSH key..."

KEY_PATH="$HOME/.ssh/id_ed25519"

if [ ! -f "$KEY_PATH" ]; then
    ssh-keygen -t ed25519 -C "chezmoi-generated" -f "$KEY_PATH" -N ""
    eval "$(ssh-agent -s)"
    ssh-add "$KEY_PATH"
    gh ssh-key add "$KEY_PATH.pub" --title "$(hostname)-$(date +%Y%m%d)"
else
    echo "SSH key already exists. Skipping generation."
fi

echo "SSH setup complete."
