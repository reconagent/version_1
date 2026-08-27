"""
Network utilities: IP address, subnet calculation.
"""
import socket
import ipaddress
import fcntl
import struct

def get_local_ip():
    """Get primary IP address of the host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_subnet(ip):
    """Return CIDR subnet for given IP (assumes /24)."""
    # Simplistic: assume /24 for RFC1918
    parts = ip.split('.')
    if len(parts) == 4:
        base = '.'.join(parts[:3])
        return f"{base}.0/24"
    return '192.168.1.0/24'
