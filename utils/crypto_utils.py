"""
Cryptography utilities using Fernet.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_fernet_key():
    """Derive a Fernet key from hostname and machine-id."""
    # Read machine-id
    try:
        with open('/etc/machine-id', 'r') as f:
            machine_id = f.read().strip()
    except:
        machine_id = 'default'
    hostname = socket.gethostname()
    salt = b'aetheric_salt'  # fixed salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(f"{hostname}{machine_id}".encode()))
    return key
