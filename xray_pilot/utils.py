"""Utility functions for Xray Pilot."""

import os
import sys
import socket
import subprocess
import platform
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_config_dir() -> str:
    """Get the default config directory path."""
    # Use project's config/ directory (relative to project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(project_root, 'config')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def sanitize_input(value: str, max_length: int = 256) -> str:
    """Sanitize user input string."""
    if not isinstance(value, str):
        raise ValueError('Input must be a string')
    value = value.strip()[:max_length]
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        if char in value:
            raise ValueError(f'Invalid character in input: {char}')
    return value


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive information in logs."""
    if len(value) <= visible_chars:
        return '*' * len(value)
    return '*' * (len(value) - visible_chars) + value[-visible_chars:]


def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def ping_host(host: str, port: int, timeout: int = 5) -> float:
    """Ping a host and return latency in milliseconds."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.time() - start) * 1000
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        logger.debug(f'Ping failed for {host}:{port}: {e}')
        return float('inf')


def check_connectivity(url: str, proxy: str = None, timeout: int = 10) -> bool:
    """Check connectivity to a URL."""
    try:
        import requests
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        resp = requests.get(url, proxies=proxies, timeout=timeout)
        return resp.status_code < 400
    except Exception as e:
        logger.debug(f'Connectivity check failed for {url}: {e}')
        return False


def set_macos_proxy(enable: bool, socks_port: int = 1080, http_port: int = 1087,
                    bypass_local: bool = True) -> None:
    """Set macOS system proxy for all enabled network services."""
    network_services = _get_all_network_services()
    if not network_services:
        logger.warning('Could not detect any network services')
        return

    for network_service in network_services:
        if enable:
            bypass_domains = _get_bypass_domains(bypass_local)
            subprocess.run(['networksetup', '-setsocksfirewallproxy', network_service,
                            '127.0.0.1', str(socks_port)], check=False)
            subprocess.run(['networksetup', '-setwebproxy', network_service,
                            '127.0.0.1', str(http_port)], check=False)
            subprocess.run(['networksetup', '-setsecurewebproxy', network_service,
                            '127.0.0.1', str(http_port)], check=False)
            if bypass_domains:
                subprocess.run(['networksetup', '-setproxybypassdomains', network_service]
                               + bypass_domains, check=False)
        else:
            subprocess.run(['networksetup', '-setsocksfirewallproxystate', network_service, 'off'],
                           check=False)
            subprocess.run(['networksetup', '-setwebproxystate', network_service, 'off'],
                           check=False)
            subprocess.run(['networksetup', '-setsecurewebproxystate', network_service, 'off'],
                           check=False)


def _get_all_network_services() -> list:
    """Get all enabled network service names."""
    result = subprocess.run(['networksetup', '-listallnetworkservices'],
                            capture_output=True, text=True, check=False)
    lines = result.stdout.strip().split('\n')
    services = []
    for line in lines[1:]:
        line = line.strip()
        if line and '*' not in line:
            services.append(line)
    return services


def _get_bypass_domains(bypass_local: bool) -> list:
    """Get proxy bypass domains."""
    domains = ['*.local', '169.254/16']
    if bypass_local:
        domains.extend(['*.cn', 'localhost', '127.0.0.1', '192.168.0.0/16',
                        '10.0.0.0/8', '172.16.0.0/12'])
    return domains


def generate_node_id(name: str, existing_ids: set = None) -> str:
    """Generate a unique node ID from name."""
    import re
    import uuid
    base_id = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
    if not base_id:
        base_id = 'node'
    if existing_ids is None:
        return base_id
    node_id = base_id
    counter = 1
    while node_id in existing_ids:
        node_id = f'{base_id}_{counter}'
        counter += 1
    return node_id


def format_timestamp(ts: str = None) -> str:
    """Format current time or given timestamp as ISO format."""
    if ts:
        return ts
    return datetime.now().isoformat()


def validate_protocol(protocol: str) -> bool:
    """Validate protocol type."""
    valid_protocols = {'vmess', 'vless', 'trojan', 'ss', 'shadowsocks'}
    return protocol.lower() in valid_protocols


def validate_port(port: int) -> bool:
    """Validate port number."""
    return 1 <= port <= 65535
