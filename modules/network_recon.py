"""
Network reconnaissance: ARP, ping sweep, nmap wrappers.
"""
import subprocess
import re
import ipaddress
import socket
import nmap
from utils.net_utils import get_local_ip, get_subnet

class NetworkRecon:
    def __init__(self):
        self.nm = nmap.PortScanner()

    def get_local_subnet(self):
        """Return CIDR string of local subnet."""
        ip = get_local_ip()
        subnet = get_subnet(ip)
        return subnet

    def ping_sweep(self, subnet):
        """Use nmap ping sweep to discover live hosts."""
        try:
            self.nm.scan(hosts=subnet, arguments='-sn -T4')
            hosts = list(self.nm.all_hosts())
            return hosts
        except Exception:
            # fallback to arp-scan if available
            return self._arp_scan(subnet)

    def _arp_scan(self, subnet):
        """Use arp-scan (if installed)."""
        try:
            output = subprocess.check_output(['arp-scan', '--localnet'], timeout=10).decode()
            ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', output)
            return list(set(ips))
        except:
            return []

    def quick_scan(self, ip):
        """Quick nmap scan for common ports."""
        try:
            self.nm.scan(ip, arguments='-sS -T4 -p 22,23,80,443,445,3306,3389,8080')
            ports = []
            for proto in self.nm[ip].all_protocols():
                if proto == 'tcp':
                    for port in self.nm[ip][proto].keys():
                        if self.nm[ip][proto][port]['state'] == 'open':
                            ports.append(port)
            return ports
        except:
            return []

    def service_scan(self, ip, ports):
        """Get service/version info for given ports."""
        port_str = ','.join(map(str, ports))
        try:
            self.nm.scan(ip, arguments=f'-sV -p {port_str}')
            services = []
            for proto in self.nm[ip].all_protocols():
                if proto == 'tcp':
                    for port in self.nm[ip][proto].keys():
                        svc = self.nm[ip][proto][port]
                        services.append({
                            'port': port,
                            'name': svc.get('name', 'unknown'),
                            'product': svc.get('product', ''),
                            'version': svc.get('version', '')
                        })
            return services
        except:
            return []
