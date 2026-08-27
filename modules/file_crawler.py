"""
Multi-threaded filesystem crawler hunting for secrets using regex.
"""
import os
import re
import threading
import time
import queue
import magic
from pathlib import Path
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class FileCrawler:
    def __init__(self, num_workers=8):
        self.num_workers = min(num_workers, os.cpu_count() or 8)
        self.file_queue = queue.Queue()
        self.results = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        # Patterns
        self.regex_patterns = [
            re.compile(r'API[_]?KEY', re.IGNORECASE),
            re.compile(r'AWS[_]?SECRET', re.IGNORECASE),
            re.compile(r'ACCESS[_]?KEY', re.IGNORECASE),
            re.compile(r'PASSWORD|PASSWD', re.IGNORECASE),
            re.compile(r'SECRET', re.IGNORECASE),
            re.compile(r'TOKEN', re.IGNORECASE),
            re.compile(r'PRIVATE[_]?KEY', re.IGNORECASE),
            re.compile(r'BEGIN RSA PRIVATE KEY'),
        ]
        self.ignore_dirs = {'/sys', '/proc', '/dev', '/run', '/snap'}

    def crawl(self, root_path='/'):
        """Start crawling from root_path."""
        logger.info("File crawler started on %s", root_path)
        self.results = []
        self.file_queue = queue.Queue()
        # Walk filesystem
        walk_thread = threading.Thread(target=self._walker, args=(root_path,))
        walk_thread.start()
        # Start workers
        workers = []
        for _ in range(self.num_workers):
            t = threading.Thread(target=self._worker)
            t.start()
            workers.append(t)
        # Wait for walker to finish
        walk_thread.join()
        # Wait for queue to empty
        self.file_queue.join()
        # Signal stop
        self.stop_event.set()
        for t in workers:
            t.join()
        return self.results

    def _walker(self, root):
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            # Filter ignore dirs
            if any(dirpath.startswith(ign) for ign in self.ignore_dirs):
                dirnames.clear()
                continue
            # Limit recursion depth? Not implemented.
            for fname in filenames:
                if self.stop_event.is_set():
                    return
                full_path = os.path.join(dirpath, fname)
                self.file_queue.put(full_path)

    def _worker(self):
        while not self.stop_event.is_set() or not self.file_queue.empty():
            try:
                file_path = self.file_queue.get(timeout=1)
            except queue.Empty:
                continue
            self._process_file(file_path)
            self.file_queue.task_done()

    def _process_file(self, file_path):
        # Check extension first (fast)
        ext = os.path.splitext(file_path)[1].lower()
        target_exts = {'.env', '.pem', '.pkcs12', '.kdbx', '.ovpn', '.rdp', '.sqlite',
                       '.bash_history', '.zsh_history', '.git', '.aws', '.kube', '.tfstate',
                       '.id_rsa', '.id_dsa', '.config'}
        # But we also want to scan .git/config, .aws/credentials etc. So we check name.
        # We'll rely on regex scanning anyway, but to reduce I/O we check extension or filename keywords.
        if not any(ext in target_exts or keyword in file_path for keyword in ['.git/config', '.aws/credentials', '.kube/config', '.bash_history', '.zsh_history']):
            # If not a likely target, skip
            return

        # Check file size: we only read first 4096 bytes
        try:
            with open(file_path, 'rb') as f:
                head = f.read(4096)
        except (IOError, OSError):
            return

        # Check if it's text using magic
        mime = magic.from_buffer(head, mime=True)
        if not mime.startswith('text/') and not mime.startswith('application/json'):
            return

        # Search for patterns
        try:
            text = head.decode('utf-8', errors='ignore')
        except:
            return
        matched = False
        for pattern in self.regex_patterns:
            if pattern.search(text):
                matched = True
                break
        if not matched:
            return

        # Found something
        finding = {
            'file_path': file_path,
            'matched_regex': 'found',
            'encrypted_content': self._encrypt_content(head),  # not implemented, placeholders
            'confidence_score': 0.8,
            'timestamp': time.time()
        }
        with self.lock:
            self.results.append(finding)

    def _encrypt_content(self, content):
        """Placeholder: return base64 or encrypted."""
        # In real code, use crypto_utils
        import base64
        return base64.b64encode(content).decode()
