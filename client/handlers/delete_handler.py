from core.protocol import Command, Response
from core.logger import logger
from core.network_utils import NetworkUtils

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
            NetworkUtils.send_command(self.client.socket, Command.DELETE)
            response = NetworkUtils.receive_response(self.client)
            if response != Response.SUCCESS:
                logger.log("DELETE", "Error al eliminar archivo")
                return 
            
            NetworkUtils.send_filename(self.client.socket, filename)
            
            # Fase 2: Procesamiento de respuesta
            response = NetworkUtils.receive_response(self.client.socket)
            
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