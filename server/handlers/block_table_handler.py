import os
import socket 
import threading
import json
from typing import List
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class BlockTableHandler:
    def __init__(self, server):
        self.server = server

    def process(self, client: socket.socket):
        """Procesa solicitud de información de tabla de bloques"""
        try:
            # Recopilar información de la tabla de bloques
            with self.server.block_table_lock:
                block_table = self._get_block_table()
        
            # Serializar y enviar respuesta
            NetworkUtils.send_json(client, block_table)    

            logger.log("BLOCK_TABLE", f"Listado enviado - {len(block_table)} bloques")
            
        except Exception as e:
            logger.log("BLOCK_TABLE", f"Error al procesar la tabla de bloques: {str(e)}")
            NetworkUtils.send_response(client, Response.SERVER_ERROR)

    def _get_block_table(self) -> List:
        """Obtiene la tabla de bloques"""
        return self.server.block_table.get_block_table()

        