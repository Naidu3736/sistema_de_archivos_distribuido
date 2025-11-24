import json
import os
import ipaddress
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from core.logger import logger

@dataclass
class Node:
    host: str = "localhost"
    port: int = 8001
    max_primary_mb: int = 800     # 80% para datos primarios
    max_replica_mb: int = 200     # 20% para réplicas
    primary_used_mb: int = 0
    replica_used_mb: int = 0

    @property
    def id(self) -> int:
        try:
            host_int = int(ipaddress.IPv4Address(self.host))
        except ipaddress.AddressValueError:
            host_int = 0x7F000001
        return (host_int << 16) | self.port

    @property
    def primary_available_mb(self) -> int:
        return self.max_primary_mb - self.primary_used_mb

    @property
    def replica_available_mb(self) -> int:
        return self.max_replica_mb - self.replica_used_mb

    @property
    def is_full_primary(self) -> bool:
        return self.primary_available_mb <= 0

    @property
    def is_full_replica(self) -> bool:
        return self.replica_available_mb <= 0

    @property
    def total_used_mb(self) -> int:
        return self.primary_used_mb + self.replica_used_mb

    @property
    def total_available_mb(self) -> int:
        return (self.max_primary_mb + self.max_replica_mb) - self.total_used_mb

    @property
    def max_total_mb(self) -> int:
        return self.max_primary_mb + self.max_replica_mb

class NodeManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, data_dir: str = "data"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, data_dir: str = "data"):
        with self._lock:
            if not self._initialized:
                self.nodes: Dict[int, Node] = None
                self.data_dir = data_dir
                self.config_file = os.path.join(data_dir, "config_nodes.json")
                self.lock = threading.RLock()
                self.load_nodes()
                self._initialized = True

    def load_nodes(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for node_id_str, node_data in data.items():
                    # Manejar compatibilidad con versiones anteriores
                    if 'max_primary_mb' in node_data:
                        # Nueva versión con espacios separados
                        node = Node(
                            host=node_data['host'],
                            port=node_data['port'],
                            max_primary_mb=node_data['max_primary_mb'],
                            max_replica_mb=node_data['max_replica_mb'],
                            primary_used_mb=node_data['primary_used_mb'],
                            replica_used_mb=node_data['replica_used_mb']
                        )
                    else:
                        # Versión anterior - migrar datos
                        max_size_mb = node_data.get('max_size_mb', 100)
                        used_size_mb = node_data.get('used_size_mb', 0)
                        # Calcular proporción 80/20
                        max_primary = int(max_size_mb * 0.8)
                        max_replica = max_size_mb - max_primary
                        # Asumir que todo el espacio usado es primario (para compatibilidad)
                        node = Node(
                            host=node_data['host'],
                            port=node_data['port'],
                            max_primary_mb=max_primary,
                            max_replica_mb=max_replica,
                            primary_used_mb=used_size_mb,
                            replica_used_mb=0
                        )
                    self.nodes[int(node_id_str)] = node

    def save_nodes(self):
        os.makedirs(self.data_dir, exist_ok=True)
        serializable_nodes = {
            str(node_id): {
                'host': node.host,
                'port': node.port,
                'max_primary_mb': node.max_primary_mb,
                'max_replica_mb': node.max_replica_mb,
                'primary_used_mb': node.primary_used_mb,
                'replica_used_mb': node.replica_used_mb
            }
            for node_id, node in self.nodes.items()
        }
        with open(self.config_file, 'w') as f:
            json.dump(serializable_nodes, f, indent=2, ensure_ascii=False)

    def add_node(self, host: str, port: int, max_primary_mb: int = 80, max_replica_mb: int = 20) -> int:
        with self.lock:
            node = Node(host=host, port=port, max_primary_mb=max_primary_mb, max_replica_mb=max_replica_mb)
            self.nodes[node.id] = node
            self.save_nodes()
            return node.id

    def allocate_primary_space(self, node_id: int, size_mb: int) -> bool:
        """Asigna espacio para datos primarios (del nodo dueño)"""
        with self.lock:
            if node_id in self.nodes and not self.nodes[node_id].is_full_primary:
                new_used = self.nodes[node_id].primary_used_mb + size_mb
                if new_used <= self.nodes[node_id].max_primary_mb:
                    self.nodes[node_id].primary_used_mb = new_used
                    self.save_nodes()
                    return True
            return False

    def allocate_replica_space(self, node_id: int, size_mb: int) -> bool:
        """Asigna espacio para datos de réplica (de otros nodos)"""
        with self.lock:
            if node_id in self.nodes and not self.nodes[node_id].is_full_replica:
                new_used = self.nodes[node_id].replica_used_mb + size_mb
                if new_used <= self.nodes[node_id].max_replica_mb:
                    self.nodes[node_id].replica_used_mb = new_used
                    self.save_nodes()
                    return True
            return False

    def free_primary_space(self, node_id: int, size_mb: int) -> bool:
        """Libera espacio de datos primarios"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].primary_used_mb = max(0, self.nodes[node_id].primary_used_mb - size_mb)
                self.save_nodes()
                return True
            return False

    def free_replica_space(self, node_id: int, size_mb: int) -> bool:
        """Libera espacio de datos de réplica"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].replica_used_mb = max(0, self.nodes[node_id].replica_used_mb - size_mb)
                self.save_nodes()
                return True
            return False

    def free_space(self, node_id: int, size_mb: int, is_primary: bool) -> bool:
        """Libera espacio (versión genérica para compatibilidad)"""
        if is_primary:
            return self.free_primary_space(node_id, size_mb)
        else:
            return self.free_replica_space(node_id, size_mb)

    def get_available_primary_nodes(self) -> List[int]:
        """Obtiene nodos con espacio disponible para datos primarios"""
        with self.lock:
            return [node_id for node_id, node in self.nodes.items() if not node.is_full_primary]

    def get_available_replica_nodes(self) -> List[int]:
        """Obtiene nodos con espacio disponible para réplicas"""
        with self.lock:
            return [node_id for node_id, node in self.nodes.items() if not node.is_full_replica]

    def get_available_nodes(self) -> List[int]:
        """Obtiene nodos con espacio disponible total (para compatibilidad)"""
        with self.lock:
            return [node_id for node_id, node in self.nodes.items() if node.total_available_mb > 0]

    def get_best_primary_node(self) -> Optional[int]:
        """Obtiene el mejor nodo para datos primarios (más espacio disponible)"""
        with self.lock:
            available_nodes = self.get_available_primary_nodes()
            if not available_nodes:
                return None
            # Ordenar por espacio disponible descendente
            available_nodes.sort(key=lambda node_id: self.nodes[node_id].primary_available_mb, reverse=True)
            return available_nodes[0]

    def get_best_replica_nodes(self, count: int = 2) -> List[int]:
        """Obtiene los mejores nodos para réplicas"""
        with self.lock:
            available_nodes = self.get_available_replica_nodes()
            if not available_nodes:
                return []
            # Ordenar por espacio disponible descendente
            available_nodes.sort(key=lambda node_id: self.nodes[node_id].replica_available_mb, reverse=True)
            return available_nodes[:count]

    def get_node_info(self, node_id: int) -> Optional[Dict]:
        """Obtiene información del nodo actual"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                return {
                    'id': node_id,
                    'host': node.host,
                    'port': node.port,
                    'max_primary_mb': node.max_primary_mb,
                    'max_replica_mb': node.max_replica_mb,
                    'primary_used_mb': node.primary_used_mb,
                    'replica_used_mb': node.replica_used_mb,
                    'primary_available_mb': node.primary_available_mb,
                    'replica_available_mb': node.replica_available_mb,
                    'total_used_mb': node.total_used_mb,
                    'total_available_mb': node.total_available_mb,
                    'max_total_mb': node.max_total_mb,
                    'is_full_primary': node.is_full_primary,
                    'is_full_replica': node.is_full_replica
                }
            return None

    def get_all_nodes(self) -> List[Dict]:
        """Lista todos los nodos con información completa"""
        with self.lock:
            return [self.get_node_info(node_id) for node_id in self.nodes.keys()]
        
    def get_all_ids(self) -> List[int]:
        """Lista los ID's de todos los nodos"""
        with self.lock:
            return List(self.nodes.keys())

    def get_id_of_node(self, host: str, port: int) -> int:
        """Obtiene el id del nodo actual"""
        node = Node(host=host, port=port)
        return node.id
    
    def get_node_address(self, node_id: int) -> Optional[Tuple[str, int]]:
        """Obtiene la dirección de un nodo"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                return (node.host, node.port)
            return None
        
    def get_node_count(self) -> int:
        """Obtiene el número total de nodos"""
        with self.lock:
            return len(self.nodes)

    def update_node_usage(self, node_id: int, primary_delta_mb: int = 0, replica_delta_mb: int = 0) -> bool:
        """Actualiza el uso de espacio de un nodo (para sincronización)"""
        with self.lock:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            new_primary = max(0, node.primary_used_mb + primary_delta_mb)
            new_replica = max(0, node.replica_used_mb + replica_delta_mb)
            
            # Verificar límites
            if new_primary > node.max_primary_mb or new_replica > node.max_replica_mb:
                return False
            
            node.primary_used_mb = new_primary
            node.replica_used_mb = new_replica
            self.save_nodes()
            return True

    def remove_node(self, node_id: int) -> bool:
        """Elimina un nodo del manager"""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                self.save_nodes()
                return True
            return False
    
    def get_total_capacity(self) -> int:
        """Obtiene la memoria total del sistema"""
        with self.lock:
            return sum(node.max_total_mb for node in self.nodes.values()) if self.nodes else 0

    def get_statistics(self) -> Dict[str, int]:
        """Obtiene estadísticas totales del cluster"""
        with self.lock:
            total_primary_capacity = sum(node.max_primary_mb for node in self.nodes.values())
            total_replica_capacity = sum(node.max_replica_mb for node in self.nodes.values())
            total_primary_used = sum(node.primary_used_mb for node in self.nodes.values())
            total_replica_used = sum(node.replica_used_mb for node in self.nodes.values())
            
            return {
                'total_primary_capacity_mb': total_primary_capacity,
                'total_replica_capacity_mb': total_replica_capacity,
                'total_capacity_mb': total_primary_capacity + total_replica_capacity,
                'total_primary_used_mb': total_primary_used,
                'total_replica_used_mb': total_replica_used,
                'total_used_mb': total_primary_used + total_replica_used,
                'total_primary_available_mb': total_primary_capacity - total_primary_used,
                'total_replica_available_mb': total_replica_capacity - total_replica_used,
                'node_count': len(self.nodes)
            }
        
# Crear instancia global
node_manager = NodeManager()