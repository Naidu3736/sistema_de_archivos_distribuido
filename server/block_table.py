import os
import pickle

class BlockTable:
    def __init__(self, total_blocks: int = 1000, data_dir: str = "data"):
        self.total_blocks = total_blocks
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.entries = [0] * total_blocks
        self.available_blocks = list(range(total_blocks))

        # Máscaras de bits
        self.STATUS_MASK = 0x80000000    # 10000000 00000000 00000000 00000000
        self.FILE_ID_MASK = 0x7FFF0000   # 01111111 11111111 00000000 00000000  
        self.NEXT_BLOCK_MASK = 0x0000FFFF # 00000000 00000000 11111111 11111111

        # Desplazamientos
        self.FILE_ID_SHIFT = 16
        self.STATUS_SHIFT = 31

        self.NULL_BLOCK = 0xFFFF

        self._load_from_disk()

    def _load_from_disk(self):
        """Carga la tabla desde disco"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        if os.path.exists(block_table_path):
            try:
                with open(block_table_path, 'rb') as f:
                    data = pickle.load(f)
                    self.entries = data['entries']
                    self.available_blocks = data['free_blocks']
                    self.next_file_id = data.get('next_file_id', 0)
                print(f"BlockTable cargada desde disco - {len(self.available_blocks)} bloques libres")
            except Exception as e:
                print(f"Error cargando BlockTable: {e}. Inicializando nueva tabla.")
                self._initialize_empty()
        else:
            self._initialize_empty()
            print("BlockTable inicializada nueva")

    def _save_to_disk(self):
        """Guarda la tabla en disco"""
        block_table_path = os.path.join(self.data_dir, "block_table.pkl")
        try:
            data = {
                'entries': self.entries,
                'free_blocks': self.available_blocks,
                'total_blocks': self.total_blocks
            }
            with open(block_table_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error guardando BlockTable: {e}")

    def _initialize_empty(self):
        """Inicializa una tabla vacía"""
        for i in range(self.total_blocks):
            self.entries[i] = 0
        self.available_blocks = list(range(self.total_blocks))

    def _set_entry(self, block_id: int, status: bool, file_id: int, next_block: int):
        """Función helper interna para establecer una entrada"""
        entry = 0
        
        # Status (bit más significativo)
        if status:
            entry |= self.STATUS_MASK
        
        # File ID (bits 30-16)
        entry |= (file_id & 0x7FFF) << self.FILE_ID_SHIFT
        
        # Next Block (bits 15-0)
        if next_block is None:
            next_block = self.NULL_BLOCK
        entry |= (next_block & 0xFFFF)
        
        self.entries[block_id] = entry

    def _get_entry_parts(self, block_id: int) -> tuple:
        """Función helper interna para obtener partes de una entrada"""
        entry = self.entries[block_id]

        # CORRECCIÓN: Aplicar desplazamientos correctamente
        status = bool(entry & self.STATUS_MASK)
        file_id = (entry & self.FILE_ID_MASK) >> self.FILE_ID_SHIFT
        next_block = entry & self.NEXT_BLOCK_MASK

        if next_block == self.NULL_BLOCK:
            next_block = None

        return status, file_id, next_block

    def allocate_blocks(self, file_id: int, num_blocks: int) -> list:
        """Asigna bloques a un archivo"""
        if len(self.available_blocks) < num_blocks:
            raise Exception(f"No hay espacio. Necesitas {num_blocks} bloques, hay {len(self.available_blocks)} libres")
        
        allocated = self.available_blocks[:num_blocks]
        self.available_blocks = self.available_blocks[num_blocks:]

        for i, block_id in enumerate(allocated):
            next_block_id = allocated[i + 1] if i < len(allocated) - 1 else None

            self._set_entry(
                block_id=block_id,
                status=True,
                file_id=file_id,
                next_block=next_block_id
            )

        self._save_to_disk()
        return allocated
    
    def free_blocks(self, first_block_id: int) -> int:
        """Libera una cadena de bloques empezando desde first_block_id"""
        blocks_freed = 0
        current = first_block_id

        while current is not None and current != self.NULL_BLOCK:
            status, file_id, next_block = self._get_entry_parts(current)

            if not status:
                break

            self._free_single_block(current)
            blocks_freed += 1
            current = next_block

        self._save_to_disk()
        return blocks_freed
    
    def _free_single_block(self, block_id: int):
        """Libera un solo bloque"""
        self._set_entry(
            block_id=block_id,
            status=False,
            file_id=0,
            next_block=None
        )

        if block_id not in self.available_blocks:
            self.available_blocks.append(block_id)
            # No es necesario ordenar si usamos como stack
            # self.available_blocks.sort()

    def get_block_chain(self, first_block_id: int) -> list:
        """Obtiene la cadena completa de bloques de un archivo"""
        chain = []
        current = first_block_id
        
        while current is not None and current != self.NULL_BLOCK:
            status, file_id, next_block = self._get_entry_parts(current)
            
            if not status:  # Bloque libre, terminar cadena
                break
                
            chain.append(current)
            current = next_block
        
        return chain
    
    def get_blocks_by_file(self, file_id: int) -> list:
        """Obtiene TODOS los bloques de un archivo (búsqueda lineal)"""
        blocks = []
        for block_id in range(self.total_blocks):
            status, current_file_id, _ = self._get_entry_parts(block_id)
            if status and current_file_id == file_id:
                blocks.append(block_id)
        return blocks
    
    def get_block_info(self, block_id: int) -> dict:
        """Obtiene información de un bloque específico"""
        status, file_id, next_block = self._get_entry_parts(block_id)
        
        return {
            "block_id": block_id,
            "status": "allocated" if status else "free",
            "file_id": file_id if status else None,
            "next_block": next_block
        }
    
    def get_system_status(self):
        """Estado del sistema"""
        used_blocks = 0
        for i in range(self.total_blocks):
            status, _, _ = self._get_entry_parts(i)
            if status:
                used_blocks += 1
        
        return {
            "total_blocks": self.total_blocks,
            "used_blocks": used_blocks,
            "free_blocks": len(self.available_blocks),
            "usage_percent": (used_blocks / self.total_blocks) * 100
        }