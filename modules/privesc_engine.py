"""
Linux privilege escalation suggester: kernel, sudo, SUID, capabilities.
"""
import subprocess
import re
import os

class PrivescEngine:
    def __init__(self):
        self.kernel = None
        self.sudo_version = None
        self.suid_binaries = []
        self.capabilities = []
        self._gather_info()

    def _gather_info(self):
        # Kernel version
        try:
            out = subprocess.check_output(['uname', '-r']).decode().strip()
            self.kernel = out
        except:
            pass
        # Sudo version
        try:
            out = subprocess.check_output(['sudo', '-V'], stderr=subprocess.STDOUT).decode()
            m = re.search(r'Sudo version (\d+\.\d+\.\d+)', out)
            if m:
                self.sudo_version = m.group(1)
        except:
            pass
        # SUID binaries (find / -perm -4000 -type f 2>/dev/null)
        try:
            out = subprocess.check_output(['find', '/', '-perm', '-4000', '-type', 'f'], stderr=subprocess.DEVNULL).decode()
            self.suid_binaries = out.splitlines()
        except:
            pass

    def suggest_exploits(self):
        """Return list of suggested exploits."""
        exploits = []
        if self.kernel:
            if '5.8' in self.kernel:
                exploits.append({'cve': 'CVE-2022-0847', 'name': 'DirtyPipe'})
        if self.sudo_version:
            # PwnKit: sudo < 1.9.12p2
            try:
                ver = tuple(map(int, self.sudo_version.split('.')))
                if ver < (1, 9, 12):
                    exploits.append({'cve': 'CVE-2021-4034', 'name': 'PwnKit'})
            except:
                pass
        # Add more based on SUID, capabilities, etc.
        return exploits
