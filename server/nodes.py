# nodes.py (VERSIÓN SINGLETON MEJORADA)
import json
import os
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from core.logger import logger

@dataclass
class Node:
    host: str = "localhost"
    port: int = 8001
    max_primary_mb: int = 100      # Espacio total para datos primarios
    max_replica_mb: int = 100      # Espacio total para réplicas
    used_primary_mb: int = 0       # Espacio usado en datos primarios
    used_replica_mb: int = 0       # Espacio usado en réplicas

    @property
    def id(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def available_primary_mb(self) -> int:
        return self.max_primary_mb - self.used_primary_mb

    @property
    def available_replica_mb(self) -> int:
        return self.max_replica_mb - self.used_replica_mb

class NodeManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, data_dir: str = "data"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NodeManager, cls).__new__(cls)
                cls._instance.initialize(data_dir)
            return cls._instance
    
    def initialize(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "nodes.json")
        self.lock = threading.RLock()
        self.nodes: Dict[str, Node] = {}
        
        # Cargar nodos existentes al inicializar
        self.load_nodes()
        
        logger.log("NODES", f"NodeManager inicializado. Nodos cargados: {len(self.nodes)}")

    def load_nodes(self) -> bool:
        """Carga los nodos desde el archivo de configuración"""
        with self.lock:
            if not os.path.exists(self.config_file):
                logger.log("NODES", "Archivo de nodos no encontrado. Se iniciará sin nodos.")
                self.nodes = {}
                return True
                
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.log("NODES", "Archivo de nodos está vacío")
                        self.nodes = {}
                        return True
                    
                    data = json.loads(content)
                    loaded_count = 0
                    
                    for node_id, node_data in data.items():
                        try:
                            self.nodes[node_id] = Node(**node_data)
                            loaded_count += 1
                        except Exception as e:
                            logger.log("NODES", f"Error cargando nodo {node_id}: {e}")
                    
                    logger.log("NODES", f"Nodos cargados exitosamente: {loaded_count}/{len(data)}")
                    return True
                    
            except json.JSONDecodeError as e:
                logger.log("NODES", f"Error decodificando JSON de nodos: {e}")
                self.nodes = {}
                return False
            except Exception as e:
                logger.log("NODES", f"Error cargando nodos: {e}")
                self.nodes = {}
                return False

    def save_nodes(self) -> bool:
        """Guarda los nodos en el archivo de configuración"""
        with self.lock:
            try:
                os.makedirs(self.data_dir, exist_ok=True)
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    # Usar asdict para serializar correctamente los dataclasses
                    nodes_data = {node_id: asdict(node) for node_id, node in self.nodes.items()}
                    json.dump(nodes_data, f, indent=2, ensure_ascii=False)
                
                logger.log("NODES", f"Nodos guardados: {len(self.nodes)}")
                return True
            except Exception as e:
                logger.log("NODES", f"Error guardando nodos: {e}")
                return False

    def add_node(self, host: str, port: int, max_primary_mb: int = 100, max_replica_mb: int = 100) -> str:
        """Agrega un nuevo nodo al manager"""
        with self.lock:
            node = Node(
                host=host, 
                port=port, 
                max_primary_mb=max_primary_mb, 
                max_replica_mb=max_replica_mb
            )
            
            if node.id in self.nodes:
                logger.log("NODES", f"El nodo {node.id} ya existe")
                return node.id
            
            self.nodes[node.id] = node
            self.save_nodes()
            
            logger.log("NODES", 
                f"Nodo agregado: {node.id} "
                f"(Primario: {max_primary_mb}MB, Réplica: {max_replica_mb}MB)"
            )
            return node.id

    def update_node(self, node_id: str, **kwargs) -> bool:
        """Actualiza la configuración de un nodo existente"""
        with self.lock:
            if node_id not in self.nodes:
                logger.log("NODES", f"Nodo {node_id} no encontrado para actualizar")
                return False
            
            node = self.nodes[node_id]
            valid_fields = {'host', 'port', 'max_primary_mb', 'max_replica_mb'}
            
            for field, value in kwargs.items():
                if field in valid_fields and hasattr(node, field):
                    setattr(node, field, value)
            
            self.save_nodes()
            logger.log("NODES", f"Nodo {node_id} actualizado")
            return True

    def remove_node(self, node_id: str) -> bool:
        """Elimina un nodo del manager"""
        with self.lock:
            if node_id not in self.nodes:
                logger.log("NODES", f"Nodo {node_id} no encontrado")
                return False
            
            # Verificar si el nodo tiene espacio usado
            node = self.nodes[node_id]
            if node.used_primary_mb > 0 or node.used_replica_mb > 0:
                logger.log("NODES", 
                    f"Advertencia: Nodo {node_id} tiene espacio usado "
                    f"(Primario: {node.used_primary_mb}MB, Réplica: {node.used_replica_mb}MB)"
                )
            
            del self.nodes[node_id]
            self.save_nodes()
            logger.log("NODES", f"Nodo eliminado: {node_id}")
            return True

    def get_total_capacity(self) -> Dict[str, int]:
        """Obtiene la capacidad total del cluster (suma de todos los nodos)"""
        with self.lock:
            total_primary = sum(node.max_primary_mb for node in self.nodes.values())
            total_replica = sum(node.max_replica_mb for node in self.nodes.values())
            total_used_primary = sum(node.used_primary_mb for node in self.nodes.values())
            total_used_replica = sum(node.used_replica_mb for node in self.nodes.values())
            
            return {
                'total_primary_mb': total_primary,
                'total_replica_mb': total_replica,
                'total_used_primary_mb': total_used_primary,
                'total_used_replica_mb': total_used_replica,
                'total_available_primary_mb': total_primary - total_used_primary,
                'total_available_replica_mb': total_replica - total_used_replica,
                'total_capacity_mb': total_primary  # Capacidad total = espacio primario total
            }

    def allocate_primary(self, node_id: str, size_mb: float) -> bool:
        """Asigna espacio para datos primarios - versión más precisa"""
        with self.lock:
            if node_id not in self.nodes:
                return False
                
            node = self.nodes[node_id]
            if node.available_primary_mb >= size_mb:
                node.used_primary_mb += size_mb
                self.save_nodes()
                logger.log("NODES", f"Primario: {size_mb:.3f}MB asignados a {node_id}")
                return True
            
            logger.log("NODES_WARNING", 
                f"Sin espacio en {node_id}: necesita {size_mb:.3f}MB, "
                f"disponible {node.available_primary_mb:.3f}MB"
            )
            return False

    def allocate_replica(self, node_id: str, size_mb: float) -> bool:
        """Asigna espacio para réplicas - versión más precisa"""
        with self.lock:
            if node_id not in self.nodes:
                return False
                
            node = self.nodes[node_id]
            if node.available_replica_mb >= size_mb:
                node.used_replica_mb += size_mb
                self.save_nodes()
                logger.log("NODES", f"Réplica: {size_mb:.3f}MB asignados a {node_id}")
                return True
            
            logger.log("NODES_WARNING", 
                f"Sin espacio para réplica en {node_id}: necesita {size_mb:.3f}MB, "
                f"disponible {node.available_replica_mb:.3f}MB"
            )
            return False

    def verify_node_space(self, node_id: str, size_mb: float, is_primary: bool) -> bool:
        """Verifica si un nodo tiene espacio sin asignarlo"""
        with self.lock:
            if node_id not in self.nodes:
                return False
                
            node = self.nodes[node_id]
            if is_primary:
                return node.available_primary_mb >= size_mb
            else:
                return node.available_replica_mb >= size_mb

    def free_primary(self, node_id: str, size_mb: int) -> bool:
        """Libera espacio de datos primarios"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.used_primary_mb = max(0, node.used_primary_mb - 1)
                self.save_nodes()
                return True
            return False

    def free_replica(self, node_id: str, size_mb: int) -> bool:
        """Libera espacio de réplicas"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.used_replica_mb = max(0, node.used_replica_mb - 1)
                self.save_nodes()
                return True
            return False
        
    def free_file_space(self, block_chain: list, file_size: int):
        """Libera espacio para una cadena de bloques - SIMPLIFICADO"""
        with self.lock:
            if not block_chain:
                return
                
            total_blocks = len(block_chain)
            logger.log("NODES", f"Liberando espacio: {total_blocks} bloques (1MB cada uno)")
            
            for logical_id, physical_number, primary_node, replica_nodes in block_chain:
                # Liberar espacio primario - SIEMPRE 1MB
                if primary_node and primary_node in self.nodes:
                    self.nodes[primary_node].used_primary_mb = max(0, 
                        self.nodes[primary_node].used_primary_mb - 1
                    )
                
                # Liberar espacio de réplicas - SIEMPRE 1MB
                for replica_node in replica_nodes:
                    if replica_node and replica_node in self.nodes:
                        self.nodes[replica_node].used_replica_mb = max(0,
                            self.nodes[replica_node].used_replica_mb - 1
                        )
            
            self.save_nodes()
            logger.log("NODES", f"Espacio liberado: {total_blocks}MB")

    def get_primary_candidates(self) -> List[str]:
        """Obtiene nodos con espacio disponible para datos primarios"""
        with self.lock:
            return [
                node_id for node_id, node in self.nodes.items() 
                if node.available_primary_mb > 0
            ]

    def get_replica_candidates(self, exclude_nodes: List[str] = None) -> List[str]:
        """Obtiene nodos con espacio disponible para réplicas"""
        with self.lock:
            exclude_set = set(exclude_nodes or [])
            candidates = [
                node_id for node_id, node in self.nodes.items()
                if node.available_replica_mb > 0 and node_id not in exclude_set
            ]
            # Ordenar por espacio disponible (descendente)
            candidates.sort(key=lambda nid: self.nodes[nid].available_replica_mb, reverse=True)
            return candidates

    def get_best_primary_node(self) -> Optional[str]:
        """Obtiene el mejor nodo para datos primarios"""
        candidates = self.get_primary_candidates()
        if not candidates:
            return None
        # Elegir el nodo con más espacio disponible
        return max(candidates, key=lambda nid: self.nodes[nid].available_primary_mb)

    def get_best_replica_nodes(self, count: int = 2, exclude_nodes: List[str] = None) -> List[str]:
        """Obtiene los mejores nodos para réplicas"""
        candidates = self.get_replica_candidates(exclude_nodes)
        return candidates[:count]

    def get_node_info(self, node_id: str) -> Optional[Dict]:
        """Obtiene información de un nodo específico"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                return {
                    'id': node_id,
                    'host': node.host,
                    'port': node.port,
                    'max_primary_mb': node.max_primary_mb,
                    'max_replica_mb': node.max_replica_mb,
                    'used_primary_mb': node.used_primary_mb,
                    'used_replica_mb': node.used_replica_mb,
                    'available_primary_mb': node.available_primary_mb,
                    'available_replica_mb': node.available_replica_mb
                }
            return None

    def get_all_nodes(self) -> List[Dict]:
        """Obtiene información de todos los nodos"""
        with self.lock:
            return [self.get_node_info(node_id) for node_id in self.nodes.keys()]

    def get_stats(self) -> Dict:
        """Obtiene estadísticas del cluster"""
        stats = self.get_total_capacity()
        stats.update({
            'total_nodes': len(self.nodes),
            'active_nodes': len(self.nodes)  # Por ahora todos se consideran activos
        })
        return stats

    def reset_usage(self) -> bool:
        """Resetea el uso de todos los nodos (útil para testing)"""
        with self.lock:
            for node in self.nodes.values():
                node.used_primary_mb = 0
                node.used_replica_mb = 0
            self.save_nodes()
            logger.log("NODES", "Uso de todos los nodos reseteado a cero")
            return True

# Instancia global singleton
node_manager = NodeManager()