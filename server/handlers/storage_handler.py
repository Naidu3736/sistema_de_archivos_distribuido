import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class StorageHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa solicitud de estado del almacenamiento"""
        try:
            # Obtener y enviar estado del sistema (con locks)
            with self.server.file_table_lock, self.server.block_table_lock:
                status = self.server.get_storage_status()
            
            NetworkUtils.send_json(client, status)
            
        except Exception as e:
            logger.log("STATUS", f'Error durante storage status: {str(e)}')
            NetworkUtils.send_response(client, Response.SERVER_ERROR)