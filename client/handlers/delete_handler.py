from core.protocol import Command, Response
from core.logger import logger

class DeleteHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self, filename: str):
        """Elimina un archivo del sistema distribuido de archivos"""
        if not self.client.ensure_connection():
            return False
            
        try:
            logger.log("DELETE", f"Solicitando eliminación: {filename}")
            
            # Fase 1: Envío de solicitud
            self.client._send_command(Command.DELETE)
            self.client._send_filename(filename)
            
            # Fase 2: Procesamiento de respuesta
            response = self.client._receive_response()
            
            if response == Response.DELETE_COMPLETE:
                logger.log("DELETE", f"Archivo eliminado: {filename}")
                return True
            elif response == Response.FILE_NOT_FOUND:
                logger.log("DELETE", f"Archivo no encontrado: {filename}")
                return False
            else:
                logger.log("DELETE", f"Error en eliminación: {response}")
                return False
            
        except Exception as e:
            logger.log("DELETE", f"Error durante eliminación: {str(e)}")
            self.client.disconnect()
            return False