from core.protocol import Command
from core.logger import logger

class StatusHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self):
        """Obtiene el estado del almacenamiento del servidor"""
        if not self.client.ensure_connection():
            return None
            
        try:
            logger.log("STATUS", "Solicitando estado del almacenamiento...")
            
            # Fase 1: Envío de comando
            self.client._send_command(Command.STORAGE_STATUS)
            
            # Fase 2: Recepción de estado
            status_info = self.client._receive_json_response()
            
            return status_info
            
        except Exception as e:
            logger.log("STATUS", f"Error obteniendo estado del almacenamiento: {str(e)}")
            self.client.disconnect()
            return None