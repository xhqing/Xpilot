"""Node management for Xray Pilot."""

import logging
import yaml

from .utils import generate_node_id, validate_protocol, validate_port, format_timestamp

logger = logging.getLogger(__name__)


class NodeError(Exception):
    """Node related errors."""
    pass


class NodeExistsError(NodeError):
    """Node already exists."""
    pass


class NodeNotFoundError(NodeError):
    """Node not found."""
    pass


class ExportError(NodeError):
    """Export error."""
    pass


class SubscriptionError(NodeError):
    """Subscription import error."""
    pass


class NodeManager:
    """Manage proxy nodes."""

    def __init__(self, config):
        self.config = config

    def add_node(self, node_info: dict) -> str:
        """Add a new node."""
        nodes_config = self.config.load_config('nodes.json')
        existing_ids = set(nodes_config.get('nodes', {}).keys())

        node_id = node_info.get('id') or generate_node_id(node_info['name'], existing_ids)

        if node_id in existing_ids:
            raise NodeExistsError(f'Node already exists: {node_id}')

        node = {
            'id': node_id,
            'name': node_info['name'],
            'protocol': node_info['protocol'].lower(),
            'address': node_info['address'],
            'port': node_info['port'],
            'status': 'active',
            'group': node_info.get('group', 'default'),
        }

        # Protocol-specific fields
        if node['protocol'] in ('vmess', 'vless'):
            node['uuid'] = node_info.get('uuid', '')
        if node['protocol'] in ('trojan', 'ss', 'shadowsocks'):
            node['password'] = node_info.get('password', '')

        # Optional fields
        for key in ('alterId', 'security', 'network', 'tls', 'servername'):
            if key in node_info:
                node[key] = node_info[key]

        # Defaults
        node.setdefault('alterId', 0)
        node.setdefault('security', 'auto')
        node.setdefault('network', 'tcp')
        node.setdefault('tls', False)
        node.setdefault('servername', '')
        node.setdefault('latency', 0)
        node.setdefault('last_check', '')

        # Validate
        if not validate_protocol(node['protocol']):
            raise NodeError(f'Unsupported protocol: {node["protocol"]}')
        if not validate_port(node['port']):
            raise NodeError(f'Invalid port: {node["port"]}')

        nodes_config.setdefault('nodes', {})[node_id] = node
        self.config.save_config('nodes.json', nodes_config)
        logger.info(f'Added node: {node_id} ({node["name"]})')
        return node_id

    def remove_node(self, node_id: str) -> None:
        """Remove a node."""
        nodes_config = self.config.load_config('nodes.json')
        nodes = nodes_config.get('nodes', {})
        if node_id not in nodes:
            raise NodeNotFoundError(f'Node not found: {node_id}')

        del nodes[node_id]
        if nodes_config.get('default_node') == node_id:
            nodes_config['default_node'] = None
        self.config.save_config('nodes.json', nodes_config)
        logger.info(f'Removed node: {node_id}')

    def get_node(self, node_id: str) -> dict:
        """Get node information."""
        nodes_config = self.config.load_config('nodes.json')
        nodes = nodes_config.get('nodes', {})
        if node_id not in nodes:
            raise NodeNotFoundError(f'Node not found: {node_id}')
        return nodes[node_id]

    def list_nodes(self, filter_group: str = None) -> list:
        """List all nodes, optionally filtered by group."""
        nodes_config = self.config.load_config('nodes.json')
        nodes = list(nodes_config.get('nodes', {}).values())
        if filter_group:
            nodes = [n for n in nodes if n.get('group') == filter_group]
        return nodes

    def update_node(self, node_id: str, updates: dict) -> None:
        """Update node information."""
        nodes_config = self.config.load_config('nodes.json')
        nodes = nodes_config.get('nodes', {})
        if node_id not in nodes:
            raise NodeNotFoundError(f'Node not found: {node_id}')

        node = nodes[node_id]
        for key, value in updates.items():
            if key in ('id',):
                continue  # Cannot change ID
            if key in ('name', 'protocol', 'address', 'port', 'uuid', 'password',
                       'alterId', 'security', 'network', 'tls', 'servername',
                       'group', 'status'):
                node[key] = value

        if 'port' in updates and not validate_port(node['port']):
            raise NodeError(f'Invalid port: {node["port"]}')

        self.config.save_config('nodes.json', nodes_config)
        logger.info(f'Updated node: {node_id}')

    def import_from_subscription(self, url: str) -> int:
        """Import nodes from subscription URL."""
        from .subscription import fetch, parse
        content = fetch(url)
        parsed_nodes = parse(content)

        if not parsed_nodes:
            raise SubscriptionError('No nodes found in subscription')

        nodes_config = self.config.load_config('nodes.json')
        existing_ids = set(nodes_config.get('nodes', {}).keys())
        imported = 0

        for node_data in parsed_nodes:
            try:
                node_id = generate_node_id(node_data['name'], existing_ids)
                node_data['id'] = node_id
                self.add_node(node_data)
                existing_ids.add(node_id)
                imported += 1
            except NodeExistsError:
                logger.debug(f'Skipping duplicate node: {node_data["name"]}')
            except NodeError as e:
                logger.warning(f'Failed to import node: {node_data["name"]} - {e}')

        logger.info(f'Imported {imported} nodes from subscription')
        return imported

    def export_nodes(self, format: str = 'json') -> str:
        """Export nodes in specified format."""
        nodes = self.list_nodes()
        if format == 'json':
            import json
            return json.dumps(nodes, indent=2, ensure_ascii=False)
        elif format == 'yaml':
            return yaml.dump(nodes, allow_unicode=True, default_flow_style=False)
        else:
            raise ExportError(f'Unsupported export format: {format}')

    def get_default_node(self) -> str:
        """Get the default node ID."""
        nodes_config = self.config.load_config('nodes.json')
        return nodes_config.get('default_node')

    def set_default_node(self, node_id: str) -> None:
        """Set the default node."""
        self.get_node(node_id)  # Validate node exists
        nodes_config = self.config.load_config('nodes.json')
        nodes_config['default_node'] = node_id
        self.config.save_config('nodes.json', nodes_config)

    def get_groups(self) -> dict:
        """Get all node groups."""
        nodes_config = self.config.load_config('nodes.json')
        return nodes_config.get('groups', {})

    def get_node_ids(self) -> list:
        """Get all node IDs."""
        nodes_config = self.config.load_config('nodes.json')
        return list(nodes_config.get('nodes', {}).keys())
