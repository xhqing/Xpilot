"""Health checking for proxy nodes."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckError(Exception):
    """Health check error."""
    pass


class HealthChecker:
    """Check node health status."""

    TEST_URL = 'https://www.google.com/generate_204'

    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager

    def check_latency(self, node: dict, timeout: int = 10) -> float:
        """Check node latency in milliseconds."""
        from .utils import ping_host
        latency = ping_host(node['address'], node['port'], timeout)
        return latency

    def check_connectivity(self, node: dict, url: str = None, timeout: int = 10) -> bool:
        """Check node connectivity via HTTP test."""
        from .utils import check_connectivity
        test_url = url or self.TEST_URL
        proxy_url = f'socks5://127.0.0.1:{self._get_socks_port()}' if self.proxy_manager else None
        return check_connectivity(test_url, proxy_url, timeout)

    def batch_check(self, node_ids: list = None) -> list:
        """Batch check multiple nodes."""
        if node_ids is None:
            from .node_manager import NodeManager
            # node_ids should be provided by caller
            return []

        results = []
        for node_id in node_ids:
            result = self._check_single_node(node_id)
            results.append(result)

        return results

    def _check_single_node(self, node_id: str) -> dict:
        """Check a single node and return result."""
        from .node_manager import NodeNotFoundError, NodeManager

        # We need access to node_manager
        result = {
            'id': node_id,
            'name': node_id,
            'latency': float('inf'),
            'connected': False,
            'error': None,
        }

        try:
            # Get node info from node_manager (set via cli)
            if hasattr(self, '_node_manager'):
                node = self._node_manager.get_node(node_id)
                result['name'] = node.get('name', node_id)

                latency = self.check_latency(node)
                result['latency'] = latency if latency != float('inf') else -1
                result['connected'] = latency != float('inf')

                # Update node latency in config
                if result['connected']:
                    updates = {
                        'latency': int(latency),
                        'last_check': datetime.now().isoformat(),
                        'status': 'active'
                    }
                    self._node_manager.update_node(node_id, updates)
            else:
                result['error'] = 'Node manager not available'

        except NodeNotFoundError:
            result['error'] = 'Node not found'
        except Exception as e:
            result['error'] = str(e)
            result['latency'] = -1

        return result

    def sort_by_latency(self, results: list) -> list:
        """Sort check results by latency."""
        valid = [r for r in results if r.get('latency', -1) > 0]
        invalid = [r for r in results if r.get('latency', -1) <= 0]
        valid.sort(key=lambda x: x['latency'])
        return valid + invalid

    def set_node_manager(self, node_manager) -> None:
        """Set node manager reference for node lookup."""
        self._node_manager = node_manager

    def _get_socks_port(self) -> int:
        """Get SOCKS proxy port from settings."""
        if self.proxy_manager and hasattr(self.proxy_manager, 'config'):
            try:
                settings = self.proxy_manager.config.load_config('settings.json')
                return settings.get('socks_port', 1080)
            except Exception:
                pass
        return 1080  # Default port
