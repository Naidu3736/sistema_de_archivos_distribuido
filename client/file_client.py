import socket
import json
from core.protocol import Command, Response
from core.logger import logger
from client.handlers import (
    UploadHandler, DownloadHandler, DeleteHandler,
    ListHandler, InfoHandler, BlockTableHandler, StatusHandler
)

class FileClient:
    def __init__(self, host_server: str = "0.0.0.0", port_server: int = 8001, buffer_size: int = 4096):
        # =========================================================================
        # CONFIGURACIÓN INICIAL DEL CLIENTE
        # =========================================================================
        self.host_server = host_server
        self.port_server = port_server
        self.BUFFER_SIZE = buffer_size
        self.socket = None
        self.is_connected = False
        
        # Inicializar handlers
        self.upload_handler = UploadHandler(self)
        self.download_handler = DownloadHandler(self)
        self.delete_handler = DeleteHandler(self)
        self.list_handler = ListHandler(self)
        self.info_handler = InfoHandler(self)
        self.block_table_handler = BlockTableHandler(self)
        self.status_handler = StatusHandler(self)
        
        logger.log("CLIENT", f"Cliente de archivos configurado - Servidor: {host_server}:{port_server}")
    
    # =========================================================================
    # GESTIÓN DE CONEXIÓN Y DESCONEXIÓN
    # =========================================================================

    def connect(self) -> bool:
        """Establece conexión persistente con el servidor"""
        if self.is_connected and self.socket:
            return True
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host_server, self.port_server))
            self.is_connected = True
            
            logger.log("CLIENT", f"Conectado al servidor {self.host_server}:{self.port_server}")
            return True
        except Exception as e:
            logger.log("CLIENT", f"Error de conexión: {str(e)}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Cierra la conexión con el servidor"""
        if self.socket:
            try:
                self.socket.send(Command.DISCONNECT.to_bytes())
            except Exception as e:
                logger.log("CLIENT", f"Error al desconectar: {str(e)}")
            self.socket.close()
            self.socket = None
            self.is_connected = False
            logger.log("CLIENT", "Desconectado del servidor")

    def ensure_connection(self):
        """Verifica y mantiene la conexión activa"""
        if not self.is_connected or not self.socket:
            return self.connect()
        return True

    # =========================================================================
    # OPERACIONES PRINCIPALES (DELEGADAS A HANDLERS)
    # =========================================================================

    def upload_file(self, file_path: str):
        return self.upload_handler.process(file_path)

    def download_file(self, filename: str, save_path: str):
        return self.download_handler.process(filename, save_path)

    def delete_file(self, filename: str):
        return self.delete_handler.process(filename)

    def list_files(self):
        return self.list_handler.process()

    def get_file_info(self, filename: str):
        return self.info_handler.process(filename)
    
    def get_storage_status(self):
        return self.status_handler.process()

    def get_block_table(self):
        return self.block_table_handler.process()

    # =========================================================================
    # MÉTODO PARA CIERRE EXPLÍCITO
    # =========================================================================

    def close(self):
        """Cierra la conexión explícitamente"""
        self.disconnect()
        logger.log("CLIENT", "Cliente cerrado explícitamente")