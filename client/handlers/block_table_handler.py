import os
import socket 
import threading
from core.protocol import Command, Response
from core.logger import logger

class BlockTableHandler:
    def __init__(self, client):
        self.client = client

    def process(self) -> list:
        """Solicita lista de bloques del sistema"""
        if not self.client.ensure_connection():
            return []
        
        try:
            logger.log("INFO", "Solicitando tabla de bloques")

            # Fase 1: Envío de comando
            self.client._send_command(Command.BLOCK_TABLE)

            # Fase 2: Recepción y procesamiento de datos
            block_table = self.client._receive_json_response()

            logger.log("INFO", f"Lista de bloques recibida - {len(block_table)} bloques")

            return block_table

        except Exception as e:
            logger.log("INFO", f"Error al procesar la tabla de bloques: {str(e)}")
            self.client._send_command(Response.FAILURE.to_bytes())
            return None
