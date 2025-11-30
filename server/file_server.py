# file_server.py (versión actualizada)
import os
import socket
import json
import threading
from core.logger import logger
from server.block_table import BlockTable
from server.file_table import FileTable
from server.nodes import node_manager
from server.node_client import NodeClient
from server.handlers import (
    UploadHandler, DownloadHandler, DeleteHandler, 
    ListHandler, InfoHandler, StorageHandler, BlockTableHandler
)

class FileServer:
    def __init__(self, temp_dir: str = "temp", 
                 buffer_size: int = 64 * 1024, data_dir: str = "data"):
        # =========================================================================
        # CONFIGURACIÓN INICIAL DEL SERVIDOR
        self.temp_dir = temp_dir
        self.data_dir = data_dir
        self.BUFFER_SIZE = buffer_size
        self.BLOCK_SIZE = 1024 * 1024  # 1MB por bloque
        
        # Locks para acceso concurrente
        self.file_table_lock = threading.RLock()
        self.block_table_lock = threading.RLock()

        self.download_delete_lock = threading.Lock()
        self.active_downloads = 0
        self.download_counter_lock = threading.Lock()
        
        # Crear directorios necesarios para operación
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
        # Inicializar componentes de nodos
        self.node_manager = node_manager
        self.node_client = NodeClient()

        cluster_capacity = self.node_manager.get_total_capacity()
        capacity_mb = cluster_capacity['total_capacity_mb']
        logger.log("DEBUG", f"capacidad: {capacity_mb}")
    
        self.capacity_mb = capacity_mb
        
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
        logger.log("SERVER", f"Nodos registrados: {len(self.node_manager.nodes)}")


    # =========================================================================
    # MÉTODOS PRINCIPALES DE PROCESAMIENTO (DELEGADOS A HANDLERS)
    # =========================================================================

    def process_upload_request(self, client: socket.socket):
        # with self.file_operation_lock:
            return self.upload_handler.process(client)

    def process_download_request(self, client: socket.socket):
        # with self.file_operation_lock:
            return self.download_handler.process(client)

    def process_delete_request(self, client: socket.socket):
        # with self.file_operation_lock:
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
    # MÉTODOS AUXILIARES COMPARTIDOS
    # =========================================================================
        
    def get_storage_status(self):
        """Obtiene el estado completo del almacenamiento"""
        block_status = self.block_table.get_system_status()
        used_space = sum(file['size'] for file in self.file_table.get_all_files())
        
        return {
            "total_blocks": block_status["total_blocks"],
            "used_blocks": block_status["used_blocks"],
            "free_blocks": block_status["free_blocks"],
            "usage_percent": block_status["usage_percent"],
            "file_count": len(self.file_table.get_all_files()),
            "used_mb": used_space / self.BLOCK_SIZE
        }
    
    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo específico incluyendo ubicación en nodos"""
        file_info = self.file_table.get_info_file(filename)
        if not file_info:
            return None

        # Obtener cadena de bloques (con lock)
        with self.block_table_lock:
            block_chain = []
            if file_info.first_block_id is not None:  
                block_chain = self.block_table.get_block_chain(file_info.first_block_id)

        # Enriquecer información con detalles de nodos
        enriched_chain = []
        for logical_id, physical_number, primary_node, replica_nodes in block_chain:

            enriched_chain.append((
                logical_id,
                physical_number,
                primary_node,
                replica_nodes,
            ))

        return {
            "filename": file_info.filename, 
            "size": file_info.total_size,   
            "created_at": file_info.created_at.isoformat(),
            "block_count": file_info.block_count,  
            "first_block_id": file_info.first_block_id,  
            "block_chain": enriched_chain
        }

    def cleanup(self):
        """Limpia recursos (para shutdown ordenado)"""
        logger.log("SERVER", "Cerrando servidor de archivos...")
        # Realizar limpieza de nodos si es necesario
        logger.log("SERVER", "Estado guardado correctamente")