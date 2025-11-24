from core.protocol import Command
from core.logger import logger
from typing import List

class ListHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self) -> List:
        """Solicita lista de archivos disponibles en el servidor"""
        if not self.client.ensure_connection():
            return []
            
        try:
            logger.log("LIST", "Solicitando lista de archivos...")
            
            # Fase 1: Envío de comando
            self.client._send_command(Command.LIST_FILES)
            
            # Fase 2: Recepción y procesamiento de datos
            files_info = self.client._receive_json_response()
            
            logger.log("LIST", f"Lista de archivos recibida: {len(files_info)} archivos")
            return files_info
            
        except Exception as e:
            logger.log("LIST", f"Error obteniendo lista de archivos: {str(e)}")
            self.client.disconnect()
            return []