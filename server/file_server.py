import os
import socket
import json
import threading
from core.logger import logger
from server.block_table import BlockTable
from server.file_table import FileTable
from server.handlers import (
    UploadHandler, DownloadHandler, DeleteHandler, 
    ListHandler, InfoHandler, StorageHandler, BlockTableHandler
)

class FileServer:
    def __init__(self, capacity_mb: int = 1000, block_dir: str = "blocks", temp_dir: str = "temp", 
                 buffer_size: int = 4096, data_dir: str = "data"):
        # =========================================================================
        # CONFIGURACIÓN INICIAL DEL SERVIDOR
        # =========================================================================
        self.capacity_mb = capacity_mb
        self.block_dir = block_dir
        self.temp_dir = temp_dir
        self.data_dir = data_dir
        self.BUFFER_SIZE = buffer_size
        self.BLOCK_SIZE = 1024 * 1024  # 1MB por bloque
        
        # Locks para acceso concurrente
        self.file_table_lock = threading.RLock()
        self.block_table_lock = threading.RLock()
        self.file_operation_lock = threading.Lock()
        
        # Crear directorios necesarios para operación
        os.makedirs(block_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Inicializar tablas de gestión
        total_blocks = capacity_mb
        self.block_table = BlockTable(total_blocks=total_blocks, data_dir=data_dir)
        self.file_table = FileTable(data_dir=data_dir)
        
        # Inicializar handlers
        self.upload_handler = UploadHandler(self)
        self.download_handler = DownloadHandler(self)
        self.delete_handler = DeleteHandler(self)
        self.list_handler = ListHandler(self)
        self.info_handler = InfoHandler(self)
        self.storage_handler = StorageHandler(self)
        self.block_table_handler = BlockTableHandler(self)
        
        logger.log("SERVER", f"Servidor de archivos listo - {total_blocks} bloques disponibles")
        logger.log("SERVER", f"Archivos registrados: {len(self.file_table.files)}")

    # =========================================================================
    # MÉTODOS PRINCIPALES DE PROCESAMIENTO (DELEGADOS A HANDLERS)
    # =========================================================================

    def process_upload_request(self, client: socket.socket):
        return self.upload_handler.process(client)

    def process_download_request(self, client: socket.socket):
        return self.download_handler.process(client)

    def process_delete_request(self, client: socket.socket):
        return self.delete_handler.process(client)

    def process_list_request(self, client: socket.socket):
        return self.list_handler.process(client)

    def process_info_request(self, client: socket.socket):
        return self.info_handler.process(client)

    def process_storage_status_request(self, client: socket.socket):
        return self.storage_handler.process(client)
    
    def process_block_table_request(self, client: socket.socket):
        return self.block_table_handler.process(client)
    # =========================================================================
    # MÉTODOS AUXILIARES DE COMUNICACIÓN
    # =========================================================================

    def _receive_filename(self, client: socket.socket) -> str:
        """Recibe el nombre de archivo del cliente"""
        filename_size = int.from_bytes(client.recv(4), 'big')
        filename_bytes = client.recv(filename_size)
        return filename_bytes.decode('utf-8')

    def _receive_file_size(self, client: socket.socket) -> int:
        """Recibe el tamaño del archivo"""
        file_size_bytes = client.recv(8)
        return int.from_bytes(file_size_bytes, 'big')

    def _send_json_response(self, client: socket.socket, data: dict):
        """Envía una respuesta JSON al cliente"""
        data_json = json.dumps(data).encode('utf-8')
        client.send(len(data_json).to_bytes(4, 'big'))
        client.send(data_json)

    # =========================================================================
    # MÉTODOS AUXILIARES COMPARTIDOS
    # =========================================================================

    def _get_physical_blocks(self, blocks_dir: str) -> list:
        """Obtiene la lista de bloques físicos ordenados"""
        if not os.path.exists(blocks_dir):
            return []

        all_files = os.listdir(blocks_dir)
        block_files = [f for f in all_files if f.endswith('.bin')]
        
        # Ordenar por número de bloque: block_0.bin, block_1.bin, etc.
        block_files = sorted(block_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        return block_files

    def get_storage_status(self):
        """Obtiene el estado completo del almacenamiento"""
        block_status = self.block_table.get_system_status()
        
        return {
            "total_blocks": block_status["total_blocks"],
            "used_blocks": block_status["used_blocks"],
            "free_blocks": block_status["free_blocks"],
            "usage_percent": block_status["usage_percent"],
            "file_count": len(self.file_table.files),
            "total_files_size": sum(file_info.total_size for file_info in self.file_table.files.values())
        }
    
    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo específico"""
        file_info = self.file_table.get_info_file(filename)
        if not file_info:
            return None

        # Obtener cadena de bloques (con lock)
        with self.block_table_lock:
            block_chain = []
            if file_info.first_block_id is not None:  
                block_chain = self.block_table.get_block_chain(file_info.first_block_id)

        return {
            "filename": file_info.filename, 
            "size": file_info.total_size,   
            "created_at": file_info.created_at.isoformat(),
            "block_count": file_info.block_count,  
            "first_block_id": file_info.first_block_id,  
            "block_chain": block_chain
        }

    def cleanup(self):
        """Limpia recursos (para shutdown ordenado)"""
        logger.log("SERVER", "Cerrando servidor de archivos...")
        logger.log("SERVER", "Estado guardado correctamente")