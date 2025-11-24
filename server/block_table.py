import os
import pickle
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from core.logger import logger

@dataclass
class Block:
    is_allocated: bool = False
    primary_node: Optional[int] = None         # host + port
    replica_nodes: List[int] = field(default_factory=list)
    physical_number: Optional[int] = None
    next_block: Optional[int] = None
    
    @property
    def blockname(self) -> str:
        """Devolver el nombre del bloque físico"""
        if self.physical_number is None:
            return ""
        else:
            return f"block_{self.physical_number:06d}.bin"

class BlockTable:
    def __init__(self, total_blocks: int = 1000, data_dir: str = "data"):
        self.total_blocks = total_blocks
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.blocks: List[Block] = []
        self.available_blocks: List[int] = []

        self._initialize_blocks()
        self._load_from_disk()

    def _initialize_blocks(self):
        """Inicializa bloques"""
        self.blocks.clear()
        self.available_blocks.clear()
        
        for i in range(self.total_blocks):
            block_info = Block(
                is_allocated=False,
                primary_node=None,  
                replica_nodes=[],
                physical_number=None,
                next_block=None
            )
            self.blocks.append(block_info)
            self.available_blocks.append(i)

    def _load_from_disk(self):
        """Carga la tabla desde disco"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        if os.path.exists(block_table_path):
            try:
                with open(block_table_path, 'rb') as f:
                    data = pickle.load(f)
                    
                    self.blocks = []
                    for block_data in data.get('blocks', []):
                        block = Block(
                            is_allocated=block_data['is_allocated'],
                            primary_node=block_data['primary_node'],
                            replica_nodes=block_data['replica_nodes'],
                            physical_number=block_data['physical_number'],
                            next_block=block_data['next_block']
                        )
                        self.blocks.append(block)
                    
                    self.available_blocks = data['available_blocks']
                    self.total_blocks = data.get('total_blocks', self.total_blocks)

                logger.log("BLOCKS", f"BlockTable cargada desde disco - {len(self.available_blocks)} bloques libres")
            except Exception as e:
                logger.log("BLOCKS", f"Error cargando BlockTable: {e}. Inicializando nueva tabla.")
                self._initialize_blocks()
        else:
            self._initialize_blocks()
            logger.log("BLOCKS", "BlockTable inicializada nueva")

    def _save_to_disk(self):
        """Guarda la tabla en disco"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        try:
            blocks_serializable = [asdict(block) for block in self.blocks]
            data = {
                'blocks': blocks_serializable,
                'available_blocks': self.available_blocks,
                'total_blocks': self.total_blocks
            }
            
            with open(block_table_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.log("BLOCKS", f"Error guardando BlockTable: {e}")

    def allocate_blocks(self, num_blocks: int, available_nodes: List) -> List[int]:
        """Asigna bloques - retorna números físicos"""
        if len(self.available_blocks) < num_blocks:
            raise Exception(f"No hay espacio. Necesitas {num_blocks} bloques, hay {len(self.available_blocks)} libres")

        if len(available_nodes) == 0 or available_nodes is None:
            raise Exception("Necesitas al menos 2 nodos para asignar bloques")

        allocated_logical_ids = self.available_blocks[:num_blocks]
        self.available_blocks = self.available_blocks[num_blocks:]

        primary_node_index = 0

        for i, logical_id in enumerate(allocated_logical_ids):
            next_logical_id = allocated_logical_ids[i + 1] if i < len(allocated_logical_ids) - 1 else None
            
            primary_node = available_nodes[primary_node_index % len(available_nodes)]

            replica_nodes = []
            if len(available_nodes) > 1:
                replica_nodes.append(available_nodes[(primary_node_index + 1) % len(available_nodes)])
            if len(available_nodes) > 2:
                replica_nodes.append(available_nodes[(primary_node_index - 1) % len(available_nodes)])

            self.blocks[logical_id].is_allocated = True
            self.blocks[logical_id].primary_node = primary_node
            self.blocks[logical_id].replica_nodes = replica_nodes
            self.blocks[logical_id].physical_number = i
            self.blocks[logical_id].next_block = next_logical_id

            primary_node_index += 1

        self._save_to_disk()
        return allocated_logical_ids
    
    def free_blocks(self, first_block_id: int) -> int:
        """Libera una cadena de bloques empezando desde first_block_id"""
        blocks_freed = 0
        current = first_block_id

        while current is not None and 0 <= current < len(self.blocks):
            block = self.blocks[current]

            if not block.is_allocated:
                break

            next_block = block.next_block
            block.is_allocated = False
            block.primary_node = None
            block.replica_nodes = []
            block.physical_number = None
            block.next_block = None

            if current not in self.available_blocks:
                self.available_blocks.append(current)
            
            blocks_freed += 1
            current = next_block
        
        self.available_blocks.sort()
        self._save_to_disk()
        return blocks_freed

    def get_block_chain(self, first_block_id: int) -> List[Tuple]:
        """Obtiene la cadena completa de bloques de un archivo - retorna números físicos"""
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
        """Obtiene información de un bloque específico"""
        if logical_id < 0 or logical_id >= len(self.blocks):
            return None
            
        block = self.blocks[logical_id]
        return {
            "logical_id": logical_id,
            "physical_number": block.physical_number,
            "status": "allocated" if block.is_allocated else "free",
            "next_block": block.next_block,
            "primary_node": block.primary_node,
            "replica_nodes": block.replica_nodes,
            "filename": block.blockname
        }
    
    def get_system_status(self):
        """Estado del sistema"""
        used_blocks = sum(1 for block in self.blocks if block.is_allocated)
        
        return {
            "total_blocks": self.total_blocks,
            "used_blocks": used_blocks,
            "free_blocks": len(self.available_blocks),
            "usage_percent": (used_blocks / self.total_blocks) * 100 if self.total_blocks > 0 else 0
        }
    
    def has_available_blocks(self, required_blocks: int) -> bool:
        """Verifica si hay suficientes bloques disponibles"""
        return len(self.available_blocks) >= required_blocks

    def add_replica(self, logical_id: int, replica_node: int):
        """Agrega un nodo réplica para un bloque"""
        if 0 <= logical_id < len(self.blocks):
            if replica_node not in self.blocks[logical_id].replica_nodes:
                self.blocks[logical_id].replica_nodes.append(replica_node)
            self._save_to_disk()

    def remove_replica(self, logical_id: int, replica_node: int):
        """Elimina un nodo réplica de un bloque"""
        if 0 <= logical_id < len(self.blocks):
            if replica_node in self.blocks[logical_id].replica_nodes:
                self.blocks[logical_id].replica_nodes.remove(replica_node)
            self._save_to_disk()

    def resize_table(self, new_total_blocks: int) -> bool:
        """Reajusta el tamaño de la tabla de bloques"""
        if new_total_blocks < len(self.blocks) - len(self.available_blocks):
            # No se puede reducir si hay bloques en uso
            logger.log("BLOCKS", f"Error: No se puede reducir a {new_total_blocks} bloques, hay {len(self.blocks) - len(self.available_blocks)} en uso")
            return False
        
        old_total = self.total_blocks
        
        if new_total_blocks > self.total_blocks:
            # Expansión: agregar nuevos bloques
            self._expand_table(new_total_blocks)
        else:
            # Reducción: eliminar bloques libres sobrantes
            self._shrink_table(new_total_blocks)
        
        self.total_blocks = new_total_blocks
        self._save_to_disk()
        
        logger.log("BLOCKS", f"Tabla reajustada: {old_total} -> {new_total_blocks} bloques")
        return True
    
    def _expand_table(self, new_total_blocks: int):
        """Expande la tabla agregando nuevos bloques libres"""
        blocks_to_add = new_total_blocks - len(self.blocks)
        
        for i in range(blocks_to_add):
            logical_id = len(self.blocks)
            block_info = Block(
                is_allocated=False,
                primary_node=None,
                replica_nodes=[],
                physical_number=None,
                next_block=None
            )
            self.blocks.append(block_info)
            self.available_blocks.append(logical_id)
        
        logger.log("BLOCKS", f"Expansión: {blocks_to_add} nuevos bloques agregados")
    
    def _shrink_table(self, new_total_blocks: int):
        """Reduce la tabla eliminando bloques libres sobrantes"""
        # Solo podemos eliminar bloques que estén libres y al final
        blocks_to_remove = len(self.blocks) - new_total_blocks
        
        # Verificar que los bloques a eliminar estén libres
        for i in range(len(self.blocks) - blocks_to_remove, len(self.blocks)):
            if self.blocks[i].is_allocated:
                raise Exception(f"No se puede reducir: bloque {i} está en uso")
        
        # Eliminar bloques del final
        self.blocks = self.blocks[:new_total_blocks]
        
        # Reconstruir lista de disponibles
        self.available_blocks = [
            i for i in range(len(self.blocks)) 
            if not self.blocks[i].is_allocated
        ]
        
        logger.log("BLOCKS", f"Reducción: {blocks_to_remove} bloques eliminados")
    
    def compact(self, target_size: int) -> Dict[int, int]:
        """
        Compacta la tabla moviendo bloques asignados que están fuera del nuevo límite
        hacia espacios libres dentro del límite.
        Retorna un diccionario {old_id: new_id} con los movimientos realizados.
        """
        moves = {}
        
        # 1. Identificar bloques que deben moverse (están más allá del nuevo límite)
        blocks_to_move = []
        for i in range(target_size, len(self.blocks)):
            if self.blocks[i].is_allocated:
                blocks_to_move.append(i)
        
        if not blocks_to_move:
            return {} # No hay nada que mover
            
        # 2. Identificar espacios libres dentro del nuevo límite
        free_slots = []
        for i in range(target_size):
            if not self.blocks[i].is_allocated:
                free_slots.append(i)
                
        # 3. Verificar si caben
        if len(free_slots) < len(blocks_to_move):
            raise Exception(f"No hay suficiente espacio libre para compactar. Necesarios: {len(blocks_to_move)}, Libres: {len(free_slots)}")
            
        # 4. Mover bloques
        for i, old_id in enumerate(blocks_to_move):
            new_id = free_slots[i]
            
            # Mover el bloque (copiar referencia y limpiar original)
            self.blocks[new_id] = self.blocks[old_id]
            self.blocks[old_id] = Block() # Bloque vacío
            
            moves[old_id] = new_id
            
        # 5. Actualizar punteros internos (next_block)
        # Solo necesitamos revisar los bloques dentro del target_size que están asignados
        for i in range(target_size):
            block = self.blocks[i]
            if block.is_allocated and block.next_block in moves:
                block.next_block = moves[block.next_block]
                
        # 6. Reconstruir available_blocks y guardar
        self.available_blocks = [
            i for i in range(len(self.blocks)) 
            if not self.blocks[i].is_allocated
        ]
        self.available_blocks.sort()
        self._save_to_disk()
        
        logger.log("BLOCKS", f"Compactación completada: {len(moves)} bloques movidos")
        return moves

    def get_allocated_blocks_info(self) -> List[dict]:
        """Obtiene información de todos los bloques asignados"""
        allocated_info = []
        for logical_id, block in enumerate(self.blocks):
            if block.is_allocated:
                allocated_info.append({
                    "logical_id": logical_id,
                    "physical_number": block.physical_number,
                    "primary_node": block.primary_node,
                    "replica_nodes": block.replica_nodes,
                    "next_block": block.next_block,
                    "filename": block.blockname
                })
        return allocated_info
    
    def get_block_table(self) -> List[Dict]:
        """Obtiene toda la tabla de bloques"""
        return [
            {
                "status": "allocated" if block.is_allocated else "free",
                "logical_id": logical_id,
                "physical_number": block.physical_number,
                "primary_node": block.primary_node,
                "replica_nodes": block.replica_nodes,
                "next_block": block.next_block,
                "filename": block.blockname
            }
            for logical_id, block in enumerate(self.blocks)
        ]