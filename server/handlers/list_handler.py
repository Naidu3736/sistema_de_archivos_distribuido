import json
import socket
from core.protocol import Response
from core.logger import logger

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
            files_json = json.dumps(files_info).encode('utf-8')
            client.send(len(files_json).to_bytes(4, 'big'))
            client.send(files_json)
            
            logger.log("LIST", f"Listado enviado - {len(files_info)} archivos")
            
        except Exception as e:
            logger.log("LIST", f'Error durante listado: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _get_all_files_info(self) -> list:
        """Obtiene información de todos los archivos registrados"""
        return self.server.file_table.get_all_files()