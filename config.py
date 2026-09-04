# config.py – load from environment, fallback to hardcoded
import os

a = os.getenv('LLM_API_KEY', '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')
b = os.getenv('LLM_API_URL', 'https://integrate.api.nvidia.com/v1')
c = os.getenv('LLM_MODEL', 'nvidia/nemotron-3.5-lightning-30b-a3b')
d = os.getenv('TARGET_CIDR', '10.11.52.0/24')
e = os.getenv('SUPABASE_URL', 'https://serlstqmqwctlllccqwr.supabase.co')
f = os.getenv('SUPABASE_KEY', 'sb_secret_12nNU6fVjZBAC5Bx9suCyw_RsrQFFee')  # fallback old key
g = os.getenv('HYDRA_WORDLIST', '/usr/share/wordlists/rockyou.txt')
HYDRA_USERLIST = os.getenv('HYDRA_USERLIST', '/usr/local/aetheric/usernames.txt')
HYDRA_PASSLIST = os.getenv('HYDRA_PASSLIST', '/usr/local/aetheric/passwords.txt')