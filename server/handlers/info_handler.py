import socket
from core.protocol import Response
from core.logger import logger

class InfoHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa solicitud de información de archivo"""
        try:
            # Fase 1: Obtención de información (con lock)
            filename = self.server._receive_filename(client)
            with self.server.file_table_lock:
                file_info = self.server.get_file_info(filename)  # ✅ Esto retorna UN solo valor
            
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return
            
            # Fase 2: Preparación y envío de respuesta
            serializable_info = self._prepare_file_info_for_serialization(file_info)
            self.server._send_json_response(client, serializable_info)
            
        except Exception as e:
            logger.log("INFO", f'Error durante info: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _prepare_file_info_for_serialization(self, file_info: dict) -> dict:
        """Prepara la información del archivo para serialización JSON"""
        return file_info