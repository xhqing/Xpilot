"""Subscription parsing for Xray Pilot."""

import base64
import json
import logging
import re

logger = logging.getLogger(__name__)


class SubscriptionError(Exception):
    """Subscription related errors."""
    pass


def fetch(url: str) -> str:
    """Fetch subscription content from URL."""
    import requests
    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'XrayPilot/0.1.0'
        })
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise SubscriptionError(f'Failed to fetch subscription: {e}')


def parse(content: str) -> list:
    """Parse subscription content into node list."""
    # Try Base64 first (most common)
    nodes = _parse_base64(content)
    if nodes:
        return nodes

    # Try JSON
    nodes = _parse_json(content)
    if nodes:
        return nodes

    # Try Clash format
    nodes = _parse_clash(content)
    if nodes:
        return nodes

    return []


def _parse_base64(content: str) -> list:
    """Parse Base64 encoded subscription."""
    try:
        # Remove whitespace and try decode
        cleaned = content.strip()
        # Add padding if needed
        missing_padding = len(cleaned) % 4
        if missing_padding:
            cleaned += '=' * (4 - missing_padding)

        decoded = base64.b64decode(cleaned).decode('utf-8', errors='ignore')

        # Each line is a share link
        nodes = []
        for line in decoded.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            node = _parse_share_link(line)
            if node:
                nodes.append(node)
        return nodes
    except Exception as e:
        logger.debug(f'Base64 parsing failed: {e}')
        return []


def _parse_json(content: str) -> list:
    """Parse JSON format subscription."""
    try:
        data = json.loads(content)
        nodes = []
        if isinstance(data, list):
            for item in data:
                node = _convert_json_node(item)
                if node:
                    nodes.append(node)
        elif isinstance(data, dict):
            if 'servers' in data:
                for item in data['servers']:
                    node = _convert_json_node(item)
                    if node:
                        nodes.append(node)
        return nodes
    except json.JSONDecodeError:
        return []


def _parse_clash(content: str) -> list:
    """Parse Clash YAML format subscription."""
    try:
        import yaml
        data = yaml.safe_load(content)
        if not isinstance(data, dict) or 'proxies' not in data:
            return []

        nodes = []
        for item in data['proxies']:
            node = _convert_clash_node(item)
            if node:
                nodes.append(node)
        return nodes
    except Exception as e:
        logger.debug(f'Clash parsing failed: {e}')
        return []


def _parse_share_link(link: str) -> dict:
    """Parse a single share link."""
    try:
        if link.startswith('vmess://'):
            return _parse_vmess_link(link)
        elif link.startswith('vless://'):
            return _parse_vless_link(link)
        elif link.startswith('trojan://'):
            return _parse_trojan_link(link)
        elif link.startswith('ss://'):
            return _parse_ss_link(link)
    except Exception as e:
        logger.debug(f'Failed to parse share link: {e}')
    return None


def _parse_vmess_link(link: str) -> dict:
    """Parse VMess share link."""
    try:
        encoded = link[8:]  # Remove vmess://
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += '=' * (4 - missing_padding)
        data = json.loads(base64.b64decode(encoded).decode('utf-8'))

        return {
            'name': data.get('ps', data.get('name', 'Unknown')),
            'protocol': 'vmess',
            'address': data.get('add', ''),
            'port': int(data.get('port', 0)),
            'uuid': data.get('id', ''),
            'alterId': int(data.get('aid', 0)),
            'security': data.get('scy', 'auto'),
            'network': data.get('net', 'tcp'),
            'tls': data.get('tls', '') == 'tls',
            'servername': data.get('sni', ''),
        }
    except Exception:
        return None


def _parse_vless_link(link: str) -> dict:
    """Parse VLESS share link."""
    try:
        # vless://uuid@host:port?params#name
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link)
        params = parse_qs(parsed.query)

        return {
            'name': parsed.fragment or 'Unknown',
            'protocol': 'vless',
            'address': parsed.hostname,
            'port': parsed.port,
            'uuid': parsed.username,
            'security': params.get('security', ['none'])[0],
            'network': params.get('type', ['tcp'])[0],
            'tls': params.get('security', ['none'])[0] != 'none',
            'servername': params.get('sni', [''])[0],
        }
    except Exception:
        return None


def _parse_trojan_link(link: str) -> dict:
    """Parse Trojan share link."""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link)
        params = parse_qs(parsed.query)

        return {
            'name': parsed.fragment or 'Unknown',
            'protocol': 'trojan',
            'address': parsed.hostname,
            'port': parsed.port,
            'password': parsed.username,
            'tls': True,
            'servername': params.get('sni', [''])[0],
        }
    except Exception:
        return None


def _parse_ss_link(link: str) -> dict:
    """Parse Shadowsocks share link."""
    try:
        from urllib.parse import urlparse
        # ss://method:password@host:port#name
        # Or ss://base64(method:password)@host:port#name
        parsed = urlparse(link)
        user_info = parsed.username + ('.' if parsed.password else '') + (parsed.password or '')

        # Try base64 decode
        try:
            decoded = base64.b64decode(user_info).decode('utf-8')
            method, password = decoded.split(':', 1)
        except Exception:
            method = parsed.username
            password = parsed.password or ''

        return {
            'name': parsed.fragment or 'Unknown',
            'protocol': 'ss',
            'address': parsed.hostname,
            'port': parsed.port,
            'password': password,
            'security': method,
        }
    except Exception:
        return None


def _convert_json_node(item: dict) -> dict:
    """Convert JSON subscription node to internal format."""
    protocol = item.get('type', item.get('protocol', '')).lower()
    protocol_map = {'vmess': 'vmess', 'vless': 'vless', 'trojan': 'trojan',
                    'shadowsocks': 'ss', 'ss': 'ss'}
    protocol = protocol_map.get(protocol, protocol)

    return {
        'name': item.get('name', 'Unknown'),
        'protocol': protocol,
        'address': item.get('server', item.get('address', '')),
        'port': item.get('port', 0),
        'uuid': item.get('uuid', ''),
        'password': item.get('password', ''),
        'alterId': item.get('alterId', 0),
        'security': item.get('cipher', item.get('security', 'auto')),
        'network': item.get('network', 'tcp'),
        'tls': item.get('tls', False),
        'servername': item.get('servername', item.get('sni', '')),
    }


def _convert_clash_node(item: dict) -> dict:
    """Convert Clash proxy node to internal format."""
    proxy_type = item.get('type', '').lower()
    protocol_map = {'vmess': 'vmess', 'vless': 'vless', 'trojan': 'trojan',
                    'shadowsocks': 'ss'}
    protocol = protocol_map.get(proxy_type, proxy_type)

    return {
        'name': item.get('name', 'Unknown'),
        'protocol': protocol,
        'address': item.get('server', ''),
        'port': item.get('port', 0),
        'uuid': item.get('uuid', ''),
        'password': item.get('password', ''),
        'alterId': item.get('alterId', 0),
        'security': item.get('cipher', item.get('security', 'auto')),
        'network': item.get('network', 'tcp'),
        'tls': item.get('tls', False),
        'servername': item.get('servername', item.get('sni', '')),
    }
