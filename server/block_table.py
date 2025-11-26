import os
import pickle
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from core.logger import logger

@dataclass
class Block:
    is_allocated: bool = False
    primary_node: Optional[str] = None
    replica_nodes: List[str] = field(default_factory=list)
    physical_number: Optional[int] = None
    next_block: Optional[int] = None
    is_reserved: bool = False
    reserved_at: Optional[float] = None

    @property
    def blockname(self) -> str:
        if self.physical_number is None:
            return ""
        return f"block_{self.physical_number:06d}.bin"

class BlockTable:
    """
    Gestiona la tabla de bloques del sistema de archivos distribuido.
    Maneja reserva temporal y confirmacion final de asignacion de bloques a nodos.
    """
    
    def __init__(self, total_blocks: int = 1000, data_dir: str = "data", reservation_timeout: int = 300):
        self.total_blocks = total_blocks
        self.data_dir = data_dir
        self.reservation_timeout = reservation_timeout
        os.makedirs(data_dir, exist_ok=True)
        self.blocks: List[Block] = []
        self.available_blocks: List[int] = []
        self.reserved_blocks: List[int] = []
        self.lock = threading.RLock()

        self._initialize_blocks()
        self._load_from_disk()

        # Thread para limpieza automatica de reservas expiradas
        self.cleanup_thread = threading.Thread(target=self._cleanup_reservations_worker, daemon=True)
        self.cleanup_thread.start()

    def _initialize_blocks(self):
        """Inicializa todos los bloques como libres"""
        self.blocks.clear()
        self.available_blocks.clear()
        self.reserved_blocks.clear()
        
        for i in range(self.total_blocks):
            self.blocks.append(Block())
            self.available_blocks.append(i)

    def _load_from_disk(self):
        """Carga el estado de la tabla desde archivo"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        if os.path.exists(block_table_path):
            try:
                with open(block_table_path, 'rb') as f:
                    data = pickle.load(f)
                    
                    self.blocks = []
                    for block_data in data.get('blocks', []):
                        self.blocks.append(Block(**block_data))
                    
                    self.available_blocks = data['available_blocks']
                    self.reserved_blocks = data.get('reserved_blocks', [])
                    self.total_blocks = data.get('total_blocks', self.total_blocks)

                logger.log("BLOCKS", f"Tabla cargada - Libres: {len(self.available_blocks)}, Reservados: {len(self.reserved_blocks)}")
            except Exception as e:
                logger.log("BLOCKS", f"Error cargando tabla: {e}. Inicializando nueva.")
                self._initialize_blocks()
        else:
            self._initialize_blocks()
            logger.log("BLOCKS", "Tabla inicializada nueva")

    def _save_to_disk(self):
        """Guarda el estado de la tabla a archivo"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        try:
            data = {
                'blocks': [asdict(block) for block in self.blocks],
                'available_blocks': self.available_blocks,
                'reserved_blocks': self.reserved_blocks,
                'total_blocks': self.total_blocks
            }
            
            with open(block_table_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.log("BLOCKS", f"Error guardando tabla: {e}")

    def _cleanup_reservations_worker(self):
        """Worker que limpia reservas expiradas periodicamente"""
        while True:
            time.sleep(60)
            self.cleanup_expired_reservations()

    def cleanup_expired_reservations(self):
        """Limpia reservas que han excedido el tiempo limite"""
        with self.lock:
            current_time = time.time()
            expired_blocks = []
            
            for logical_id in self.reserved_blocks:
                block = self.blocks[logical_id]
                if (block.reserved_at is not None and 
                    current_time - block.reserved_at > self.reservation_timeout):
                    expired_blocks.append(logical_id)
            
            if expired_blocks:
                for logical_id in expired_blocks:
                    self._cancel_reservation_internal(logical_id)
                
                logger.log("BLOCKS", f"Reservas expiradas limpiadas: {len(expired_blocks)} bloques")
                self._save_to_disk()

    def _cancel_reservation_internal(self, logical_id: int):
        """Cancela una reserva internamente (sin lock externo)"""
        if logical_id in self.reserved_blocks:
            block = self.blocks[logical_id]
            block.is_reserved = False
            block.reserved_at = None
            
            self.reserved_blocks.remove(logical_id)
            if logical_id not in self.available_blocks:
                self.available_blocks.append(logical_id)
            self.available_blocks.sort()

    def reserve_blocks(self, num_blocks: int) -> List[int]:
        """Reserva bloques temporalmente sin asignar nodos"""
        with self.lock:
            if len(self.available_blocks) < num_blocks:
                raise Exception(f"No hay suficientes bloques libres. Necesarios: {num_blocks}, Disponibles: {len(self.available_blocks)}")

            reserved_ids = self.available_blocks[:num_blocks]
            self.available_blocks = self.available_blocks[num_blocks:]
            self.reserved_blocks.extend(reserved_ids)
            
            current_time = time.time()
            for logical_id in reserved_ids:
                block = self.blocks[logical_id]
                block.is_reserved = True
                block.reserved_at = current_time
            
            self._save_to_disk()
            logger.log("BLOCKS", f"Bloques reservados: {reserved_ids}")
            return reserved_ids

    def confirm_block_allocation(self, logical_id: int, primary_node: str, replica_nodes: List[str], 
                               physical_number: int, next_block: Optional[int] = None):
        """Confirma la asignación final de un bloque con sus nodos"""
        with self.lock:
            if logical_id not in self.reserved_blocks:
                raise Exception(f"Bloque {logical_id} no está reservado")
            
            block = self.blocks[logical_id]
            
            # Confirmar asignación final
            block.is_allocated = True
            block.is_reserved = False
            block.reserved_at = None
            block.primary_node = primary_node
            block.replica_nodes = replica_nodes
            block.physical_number = physical_number
            block.next_block = next_block
            
            self.reserved_blocks.remove(logical_id)
            
            self._save_to_disk()
            logger.log("BLOCKS", f"Bloque {logical_id} confirmado - Primario: {primary_node}, Réplicas: {len(replica_nodes)}")

    def cancel_blocks_reservation(self, block_ids: List[int]):
        """Cancela la reserva de multiples bloques"""
        with self.lock:
            for logical_id in block_ids:
                self._cancel_reservation_internal(logical_id)
            self._save_to_disk()
            logger.log("BLOCKS", f"Reservas canceladas para {len(block_ids)} bloques")

    def allocate_blocks_distributed(self, num_blocks: int, node_assignments: List[Tuple[str, List[str]]]) -> List[int]:
        """
        Asigna bloques distribuidos con confirmacion final.
        node_assignments: Lista de (nodo_primario, [nodos_replica]) para cada bloque
        """
        if len(node_assignments) != num_blocks:
            raise Exception("El numero de asignaciones debe coincidir con el numero de bloques")
        
        # 1. Reservar bloques temporalmente
        reserved_ids = self.reserve_blocks(num_blocks)
        
        try:
            # 2. Confirmar cada bloque con sus nodos (esto se hace DESPUES de verificar los nodos)
            for i, logical_id in enumerate(reserved_ids):
                primary_node, replica_nodes = node_assignments[i]
                next_block = reserved_ids[i + 1] if i < len(reserved_ids) - 1 else None
                
                self.confirm_block_allocation(
                    logical_id=logical_id,
                    primary_node=primary_node,
                    replica_nodes=replica_nodes,
                    physical_number=i,
                    next_block=next_block
                )
            
            logger.log("BLOCKS", f"Asignacion distribuida completada: {num_blocks} bloques")
            return reserved_ids
            
        except Exception as e:
            # Si falla algo, cancelar todas las reservas
            self.cancel_blocks_reservation(reserved_ids)
            raise e

    def free_blocks_chain(self, first_block_id: int) -> int:
        """Libera una cadena completa de bloques a partir del primer bloque"""
        with self.lock:
            blocks_freed = 0
            current = first_block_id

            while current is not None and 0 <= current < len(self.blocks):
                block = self.blocks[current]

                if not block.is_allocated:
                    break

                next_block = block.next_block
                
                # Resetear bloque a estado libre
                block.is_allocated = False
                block.primary_node = None
                block.replica_nodes = []
                block.physical_number = None
                block.next_block = None
                block.is_reserved = False
                block.reserved_at = None

                if current not in self.available_blocks:
                    self.available_blocks.append(current)
                
                if current in self.reserved_blocks:
                    self.reserved_blocks.remove(current)
                
                blocks_freed += 1
                current = next_block
            
            self.available_blocks.sort()
            self._save_to_disk()
            return blocks_freed

    def get_block_chain(self, first_block_id: int) -> List[Tuple]:
        """Obtiene la cadena de bloques de un archivo"""
        with self.lock:
            chain = []
            current = first_block_id
            
            while current is not None and 0 <= current < len(self.blocks):
                block = self.blocks[current]
                
                if not block.is_allocated:
                    break
                    
                chain.append((
                    current,
                    block.physical_number,
                    block.primary_node,
                    block.replica_nodes
                ))
                current = block.next_block
            
            return chain
    
    def get_block_info(self, logical_id: int) -> Dict:
        """Obtiene informacion detallada de un bloque"""
        with self.lock:
            if logical_id < 0 or logical_id >= len(self.blocks):
                return None
                
            block = self.blocks[logical_id]
            status = "allocated" if block.is_allocated else "reserved" if block.is_reserved else "free"
            
            return {
                "logical_id": logical_id,
                "physical_number": block.physical_number,
                "status": status,
                "next_block": block.next_block,
                "primary_node": block.primary_node,
                "replica_nodes": block.replica_nodes,
                "filename": block.blockname
            }
    
    def get_system_status(self):
        """Obtiene el estado general del sistema de bloques"""
        with self.lock:
            used_blocks = sum(1 for block in self.blocks if block.is_allocated)
            reserved_blocks = len(self.reserved_blocks)
            
            return {
                "total_blocks": self.total_blocks,
                "used_blocks": used_blocks,
                "reserved_blocks": reserved_blocks,
                "free_blocks": len(self.available_blocks),
                "usage_percent": (used_blocks / self.total_blocks) * 100 if self.total_blocks > 0 else 0
            }
    
    def has_available_blocks(self, required_blocks: int) -> bool:
        """Verifica si hay suficientes bloques disponibles"""
        with self.lock:
            return len(self.available_blocks) >= required_blocks

    def get_reservation_time_remaining(self, logical_id: int) -> Optional[float]:
        """Obtiene el tiempo restante de una reserva"""
        with self.lock:
            if logical_id not in self.reserved_blocks:
                return None
                
            block = self.blocks[logical_id]
            if block.reserved_at is None:
                return None
                
            elapsed = time.time() - block.reserved_at
            remaining = self.reservation_timeout - elapsed
            return max(0, remaining)

    def get_block_table(self) -> List[Dict]:
        """Obtiene la tabla completa de bloques"""
        with self.lock:
            return [self.get_block_info(i) for i in range(len(self.blocks))]