import os
import socket
from core.protocol import Command, Response
from core.logger import logger

class UploadHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self, file_path: str):
        """Sube un archivo al sistema distribuido de archivos en streaming"""
        if not self.client.ensure_connection():
            return False
        
        if not self._validate_local_file(file_path):
            return False
            
        try:
            logger.log("UPLOAD", "Iniciando subida de archivo en streaming...")
            
            # Fase 1: Envío de comando y metadatos
            self.client._send_command(Command.UPLOAD)
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.log("UPLOAD", f"Subiendo archivo: {filename} ({file_size} bytes)")
            self._send_file_metadata(filename, file_size)

            # Fase 2: Esperar confirmación del servidor para proceder
            response = self.client._receive_response()
            if response != Response.SUCCESS:
                self._handle_upload_error(response, filename)
                return False
            
            # Fase 3: Envío del contenido en streaming
            self._stream_file_content(file_path, file_size)
    
            # Fase 4: Verificación de respuesta
            response = self.client._receive_response()
            if response == Response.UPLOAD_COMPLETE:
                logger.log("UPLOAD", f"Carga de archivo completada: {filename}")
                return True
            else:
                logger.log("UPLOAD", f"Error al cargar archivo: {response}")
                return False
            
        except Exception as e:
            logger.log("UPLOAD", f"Error durante subida: {str(e)}")
            self.client.disconnect()
            return False

    def _send_file_metadata(self, filename: str, file_size: int):
        """Envía metadatos del archivo al servidor"""
        filename_bytes = filename.encode('utf-8')
        
        # Enviar nombre y tamaño
        self.client.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        self.client.socket.send(filename_bytes)
        self.client.socket.send(file_size.to_bytes(8, 'big'))
        
        logger.log("UPLOAD", f"Metadata enviada: {filename} - {file_size} bytes")

    def _stream_file_content(self, file_path: str, file_size: int):
        """Envía el contenido completo del archivo al servidor en streaming"""
        filename = os.path.basename(file_path)
        logger.log("UPLOAD", f"Transmitiendo contenido del archivo en streaming...")
        
        with open(file_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(self.client.BUFFER_SIZE)
                if not chunk:
                    break
                self.client.socket.send(chunk)
                bytes_sent += len(chunk)
                
                # Mostrar progreso cada 1MB
                if bytes_sent % (1024 * 1024) == 0 or bytes_sent == file_size:
                    mb_sent = bytes_sent / (1024 * 1024)
                    mb_total = file_size / (1024 * 1024)
                    logger.log("UPLOAD", f"Progreso transmisión: {mb_sent:.1f} / {mb_total:.1f} MB")

        logger.log("UPLOAD", f"Transmisión completada: {bytes_sent} bytes enviados")

    def _handle_upload_error(self, response: Response, filename: str):
        """Maneja errores específicos durante el upload"""
        if response == Response.FILE_ALREADY_EXISTS:
            logger.log("UPLOAD", f"Error: El archivo ya existe en el servidor - {filename}")
        elif response == Response.STORAGE_FULL:
            logger.log("UPLOAD", f"Error: Capacidad de almacenamiento insuficiente para {filename}")
        else:
            logger.log("UPLOAD", f"Error en subida: {response}")

    def _validate_local_file(self, file_path: str):
        """Valida que el archivo local exista"""
        if not os.path.exists(file_path):
            logger.log("CLIENT", f"Error: Archivo no encontrado - {file_path}")
            return False
        return True