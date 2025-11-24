from core.protocol import Command
from core.logger import logger

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
            self.client._send_command(Command.FILE_INFO)
            self.client._send_filename(filename)
            
            # Fase 2: Recepción de información
            file_info = self.client._receive_json_response()
            
            return file_info
            
        except Exception as e:
            logger.log("INFO", f"Error obteniendo información del archivo: {str(e)}")
            self.client.disconnect()
            return None