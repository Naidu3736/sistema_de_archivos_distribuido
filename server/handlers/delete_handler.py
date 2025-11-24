import os
import socket
import shutil
from core.protocol import Response
from core.logger import logger

class DeleteHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de eliminación de archivo"""
        try:
            # Fase 1: Verificación de existencia (con lock)
            filename = self.server._receive_filename(client)
            with self.server.file_table_lock:
                file_info = self.server.file_table.get_info_file(filename)
                
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            # Fase 2: Eliminación lógica y física (con locks)
            with self.server.file_operation_lock:
                self._delete_file(filename, file_info)
            
            client.send(Response.DELETE_COMPLETE.to_bytes())
            logger.log("DELETE", f"Archivo eliminado: {filename}")

        except Exception as e:
            logger.log("DELETE", f'Error durante eliminación: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _delete_file(self, filename: str, file_info):
        """Elimina completamente un archivo del sistema (con locks)"""
        file_id = self.server.file_table.name_to_id[filename]

        # Liberar bloques lógicos (con lock)
        with self.server.block_table_lock:
            blocks_freed = self._free_logical_blocks(file_info)
        
        # Eliminar de FileTable (con lock)
        with self.server.file_table_lock:
            self.server.file_table.delete_file(file_id)

        # Eliminar archivos físicos (sin lock - solo I/O)
        self._delete_physical_blocks(filename)
        
        logger.log("DELETE", f"Archivo eliminado: {filename} (bloques liberados: {blocks_freed})")

    def _free_logical_blocks(self, file_info) -> int:
        """Libera los bloques lógicos asignados al archivo"""
        if file_info.first_block_id is not None:
            return self.server.block_table.free_blocks(file_info.first_block_id)
        return 0

    def _delete_physical_blocks(self, filename: str):
        """Elimina los archivos físicos del archivo"""
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.server.block_dir, sub_dir)
        
        if os.path.exists(blocks_dir):
            shutil.rmtree(blocks_dir)
            logger.log("DELETE", f"Directorio eliminado: {blocks_dir}")