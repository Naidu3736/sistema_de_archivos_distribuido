from core.protocol import Command
from core.logger import logger
from typing import List
from core.network_utils import NetworkUtils

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
            NetworkUtils.send_command(self.client.socket, Command.LIST)
            
            # Fase 2: Recepción y procesamiento de datos
            files_info = NetworkUtils.receive_json(self.client.socket)
            
            logger.log("LIST", f"Lista de archivos recibida: {len(files_info)} archivos")
            return files_info
            
        except Exception as e:
            logger.log("LIST", f"Error obteniendo lista de archivos: {str(e)}")
            self.client.disconnect()
            return []
