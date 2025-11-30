import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class InfoHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa solicitud de información de archivo"""
        try:
            # Fase 1: Obtención de información (con lock)
            filename = NetworkUtils.receive_filename(client)
            with self.server.file_table_lock:
                file_info = self.server.get_file_info(filename)
            
            if not file_info:
                NetworkUtils.send_response(client, Response.FILE_NOT_FOUND)
                return
            
            # Fase 2: Preparación y envío de respuesta
            serializable_info = self._prepare_file_info_for_serialization(file_info)
            NetworkUtils.send_json(client, serializable_info)
            
        except Exception as e:
            logger.log("INFO", f'Error durante info: {str(e)}')
            NetworkUtils.send_response(client, Response.SERVER_ERROR)

    def _prepare_file_info_for_serialization(self, file_info: dict) -> dict:
        """Prepara la información del archivo para serialización JSON"""
        return file_info