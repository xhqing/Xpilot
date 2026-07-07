"""Tests for NodeManager module."""

import pytest

from xray_pilot.config import Config
from xray_pilot.node_manager import (
    NodeManager, NodeExistsError, NodeNotFoundError, ExportError
)


@pytest.fixture
def config():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Config(tmpdir)
        cfg.init_default_configs()
        yield cfg


@pytest.fixture
def manager(config):
    return NodeManager(config)


class TestNodeManager:
    def test_add_vmess_node(self, manager):
        """测试：添加 VMess 协议节点，验证节点 ID 自动生成及字段正确保存。"""
        node_info = {
            'name': 'Test VMess',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'test-uuid-1234',
        }
        node_id = manager.add_node(node_info)
        assert node_id == 'test_vmess'

        node = manager.get_node(node_id)
        assert node['name'] == 'Test VMess'
        assert node['protocol'] == 'vmess'
        assert node['uuid'] == 'test-uuid-1234'

    def test_add_trojan_node(self, manager):
        """测试：添加 Trojan 协议节点，验证 password 字段正确保存。"""
        node_info = {
            'name': 'Test Trojan',
            'protocol': 'trojan',
            'address': 'trojan.example.com',
            'port': 443,
            'password': 'secret',
        }
        node_id = manager.add_node(node_info)
        assert 'test_trojan' in node_id

    def test_add_duplicate_node(self, manager):
        """测试：添加已存在 ID 的节点时应抛出 NodeExistsError。"""
        node_info = {
            'id': 'my_node',
            'name': 'My Node',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-1',
        }
        manager.add_node(node_info)
        with pytest.raises(NodeExistsError):
            manager.add_node(node_info)

    def test_remove_node(self, manager):
        """测试：删除已存在的节点，删除后再次获取应抛出 NodeNotFoundError。"""
        node_info = {
            'name': 'To Remove',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-remove',
        }
        node_id = manager.add_node(node_info)
        manager.remove_node(node_id)
        with pytest.raises(NodeNotFoundError):
            manager.get_node(node_id)

    def test_remove_nonexistent_node(self, manager):
        """测试：删除不存在的节点时应抛出 NodeNotFoundError。"""
        with pytest.raises(NodeNotFoundError):
            manager.remove_node('nonexistent')

    def test_list_nodes(self, manager):
        """测试：列出所有节点，验证添加的节点全部出现在列表中。"""
        for i in range(3):
            manager.add_node({
                'name': f'Node {i}',
                'protocol': 'vmess',
                'address': 'example.com',
                'port': 443 + i,
                'uuid': f'uuid-{i}',
            })
        nodes = manager.list_nodes()
        assert len(nodes) == 3

    def test_list_nodes_filter_group(self, manager):
        """测试：按分组名称过滤节点，只返回匹配分组的节点。"""
        manager.add_node({
            'name': 'Work Node',
            'protocol': 'vmess',
            'address': 'work.example.com',
            'port': 443,
            'uuid': 'uuid-work',
            'group': 'work',
        })
        manager.add_node({
            'name': 'Default Node',
            'protocol': 'vmess',
            'address': 'default.example.com',
            'port': 443,
            'uuid': 'uuid-default',
        })
        work_nodes = manager.list_nodes(filter_group='work')
        assert len(work_nodes) == 1
        assert work_nodes[0]['group'] == 'work'

    def test_update_node(self, manager):
        """测试：修改节点的名称和地址，验证更新后读取到新值。"""
        node_info = {
            'name': 'Update Me',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-update',
        }
        node_id = manager.add_node(node_info)
        manager.update_node(node_id, {'name': 'Updated Name', 'address': 'new.example.com'})
        node = manager.get_node(node_id)
        assert node['name'] == 'Updated Name'
        assert node['address'] == 'new.example.com'

    def test_update_nonexistent_node(self, manager):
        """测试：修改不存在的节点时应抛出 NodeNotFoundError。"""
        with pytest.raises(NodeNotFoundError):
            manager.update_node('nonexistent', {'name': 'New'})

    def test_set_default_node(self, manager):
        """测试：设置默认节点后，get_default_node 应返回该节点 ID。"""
        node_info = {
            'name': 'Default',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-default',
        }
        node_id = manager.add_node(node_info)
        manager.set_default_node(node_id)
        assert manager.get_default_node() == node_id

    def test_export_json(self, manager):
        """测试：将节点导出为 JSON 格式，验证可正确解析且数量正确。"""
        manager.add_node({
            'name': 'Export Test',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-export',
        })
        output = manager.export_nodes(format='json')
        import json
        nodes = json.loads(output)
        assert len(nodes) == 1

    def test_export_yaml(self, manager):
        """测试：将节点导出为 YAML 格式，验证输出包含节点名称。"""
        manager.add_node({
            'name': 'Export Test',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-export',
        })
        output = manager.export_nodes(format='yaml')
        assert 'Export Test' in output

    def test_export_invalid_format(self, manager):
        """测试：使用不支持的格式（如 xml）导出时应抛出 ExportError。"""
        with pytest.raises(ExportError):
            manager.export_nodes(format='xml')

    def test_get_node_ids(self, manager):
        """测试：获取所有节点 ID 列表，验证添加的节点 ID 在列表中。"""
        manager.add_node({
            'name': 'ID Test',
            'protocol': 'vmess',
            'address': 'example.com',
            'port': 443,
            'uuid': 'uuid-id',
        })
        ids = manager.get_node_ids()
        assert 'id_test' in ids

    def test_get_groups(self, manager):
        """测试：获取所有分组信息，验证默认分组 default 存在。"""
        groups = manager.get_groups()
        assert 'default' in groups
