from core.protocol import Command
from core.logger import logger
from core.network_utils import NetworkUtils

class InfoHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self, filename: str):
        """Obtiene información detallada de un archivo específico"""
        if not self.client.ensure_connection():
            return None
            
        try:
            logger.log("INFO", f"Solicitando información de: {filename}")
            
            # Fase 1: Envío de solicitud
            NetworkUtils.send_command(self.client.socket, Command.INFO)
            NetworkUtils.send_filename(self.client.socket, filename)
            
            # Fase 2: Recepción de información
            file_info = NetworkUtils.receive_json(self.client.socket)
            
            return file_info
            
        except Exception as e:
            logger.log("INFO", f"Error obteniendo información del archivo: {str(e)}")
            self.client.disconnect()
            return None