"""Tests for HealthChecker module."""

import pytest

from xray_pilot.health_checker import HealthChecker


@pytest.fixture
def checker():
    return HealthChecker()


class TestHealthChecker:
    def test_check_latency_timeout(self, checker):
        """测试：对不可达主机进行延迟检测，超时后应返回 float('inf')。"""
        node = {'address': '192.0.2.1', 'port': 12345}
        latency = checker.check_latency(node, timeout=1)
        assert latency == float('inf')

    def test_check_connectivity_timeout(self, checker):
        """测试：对不可达 URL 进行连通性检测，超时后应返回 False。"""
        node = {'address': '192.0.2.1', 'port': 12345}
        result = checker.check_connectivity(node, url='http://192.0.2.1', timeout=1)
        assert result is False

    def test_sort_by_latency(self, checker):
        """测试：按延迟从小到大排序节点，连通失败的节点排在最后。"""
        results = [
            {'id': 'c', 'latency': 150, 'connected': True},
            {'id': 'a', 'latency': 50, 'connected': True},
            {'id': 'b', 'latency': -1, 'connected': False},
            {'id': 'd', 'latency': 100, 'connected': True},
        ]
        sorted_results = checker.sort_by_latency(results)
        assert sorted_results[0]['id'] == 'a'
        assert sorted_results[1]['id'] == 'd'
        assert sorted_results[2]['id'] == 'c'
        assert sorted_results[3]['id'] == 'b'

    def test_sort_by_latency_empty(self, checker):
        """测试：对空列表进行延迟排序，应返回空列表。"""
        assert checker.sort_by_latency([]) == []
