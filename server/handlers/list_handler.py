import json
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class ListHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de listado de archivos"""
        try:
            # Recopilar información de todos los archivos (con lock)
            with self.server.file_table_lock:
                files_info = self._get_all_files_info()
            
            # Serializar y enviar respuesta
            NetworkUtils.send_json(client,files_info)
            
            logger.log("LIST", f"Listado enviado - {len(files_info)} archivos")
            
        except Exception as e:
            logger.log("LIST", f'Error durante listado: {str(e)}')
            NetworkUtils.send_response(client, Response.SERVER_ERROR)

    def _get_all_files_info(self) -> list:
        """Obtiene información de todos los archivos registrados"""
        return self.server.file_table.get_all_files()