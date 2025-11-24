import json
import os
import ipaddress
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from core.logger import logger

@dataclass
class Node:
    host: str = "localhost"
    port: int = 8001
    max_size_mb: int = 100
    used_size_mb: int = 0

    @property
    def id(self) -> int:
        try:
            host_int = int(ipaddress.IPv4Address(self.host))
        except ipaddress.AddressValueError:
            host_int = 0x7F000001
        return (host_int << 16) | self.port

    @property
    def available_space_mb(self) -> int:
        return self.max_size_mb - self.used_size_mb

    @property
    def is_full(self) -> bool:
        return self.available_space_mb <= 0

class NodeManager:
    def __init__(self, data_dir: str = "data"):
        self.nodes: Dict[int, Node] = {}
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "config_nodes.json")
        self.lock = threading.RLock()
        self.load_nodes()

    def load_nodes(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for node_id_str, node_data in data.items():
                    node = Node(
                        host=node_data['host'],
                        port=node_data['port'],
                        max_size_mb=node_data['max_size_mb'],
                        used_size_mb=node_data['used_size_mb']
                    )
                    self.nodes[int(node_id_str)] = node

    def save_nodes(self):
        os.makedirs(self.data_dir, exist_ok=True)
        serializable_nodes = {
            str(node_id): asdict(node) 
            for node_id, node in self.nodes.items()
        }
        with open(self.config_file, 'w') as f:
            json.dump(serializable_nodes, f, indent=2, ensure_ascii=False)

    def add_node(self, host: str, port: int, max_size_mb: int = 100) -> int:
        with self.lock:
            node = Node(host=host, port=port, max_size_mb=max_size_mb)
            self.nodes[node.id] = node
            self.save_nodes()
            return node.id

    def allocate_space(self, node_id: int, size_mb: int) -> bool:
        with self.lock:
            if node_id in self.nodes and not self.nodes[node_id].is_full:
                new_used = self.nodes[node_id].used_size_mb + size_mb
                if new_used <= self.nodes[node_id].max_size_mb:
                    self.nodes[node_id].used_size_mb = new_used
                    self.save_nodes()
                    return True
            return False

    def free_space(self, node_id: int, size_mb: int) -> bool:
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].used_size_mb = max(0, self.nodes[node_id].used_size_mb - size_mb)
                self.save_nodes()
                return True
            return False

    def get_available_nodes(self) -> List[int]:
        with self.lock:
            return [node_id for node_id, node in self.nodes.items() if not node.is_full]

    def get_node_info(self, node_id: int) -> Optional[Dict]:
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                return {
                    'id': node_id,
                    'host': node.host,
                    'port': node.port,
                    'max_size_mb': node.max_size_mb,
                    'used_size_mb': node.used_size_mb,
                    'available_space_mb': node.available_space_mb,
                    'is_full': node.is_full
                }
            return None

    def list_all_nodes(self) -> List[Dict]:
        with self.lock:
            return [self.get_node_info(node_id) for node_id in self.nodes.keys()]

    def get_current_node_id(self, host: str, port: int) -> int:
        node = Node(host=host, port=port)
        return node.id