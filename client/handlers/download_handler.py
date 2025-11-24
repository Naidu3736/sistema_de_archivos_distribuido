import os
import socket
from core.protocol import Command, Response
from core.logger import logger
from core.network_utils import NetworkUtils

class DownloadHandler:
    def __init__(self, client):
        self.client = client
        
    def process(self, filename: str, save_path: str):
        """Descarga un archivo del sistema distribuido de archivos en streaming"""
        if not self.client.ensure_connection():
            return False
            
        try:
            logger.log("DOWNLOAD", f"Solicitando descarga: {filename}")
            
            # Fase 1: Solicitud de descarga
            NetworkUtils.send_command(self.client.socket, Command.DOWNLOAD)
            NetworkUtils.send_filename(self.client.socket, filename)
            
            # Fase 2: Verificación de disponibilidad
            if not self._validate_download_availability(filename):
                return False
            
            # Fase 3: Recepción y reconstrucción en streaming
            success = self._receive_and_save_streaming_file(save_path, filename)
            
            return success
            
        except Exception as e:
            logger.log("DOWNLOAD", f"Error durante descarga: {str(e)}")
            self.client.disconnect()
            return False

    def _validate_download_availability(self, filename: str):
        """Valida que el archivo esté disponible para descarga"""
        response = NetworkUtils.receive_response(self.client.socket)
        
        if response == Response.FILE_NOT_FOUND:
            logger.log("DOWNLOAD", f"Archivo no encontrado en servidor: {filename}")
            return False
        
        elif response != Response.SUCCESS:
            logger.log("DOWNLOAD", f"Error del servidor: {response}")
            return False
        
        return True

    def _receive_and_save_streaming_file(self, save_path: str, filename: str):
        """Recibe y guarda un archivo en streaming desde el servidor"""
        # Fase 1: Recibir metadatos del streaming
        received_filename, block_count = self._receive_streaming_metadata()
        
        if received_filename != filename:
            logger.log("DOWNLOAD", f"Nombre de archivo no coincide: esperado {filename}, recibido {received_filename}")
            return False
        
        logger.log("DOWNLOAD", f"Recibiendo archivo en streaming: {filename} - {block_count} bloques")
        
        # Fase 2: Crear archivo de destino
        file_path = os.path.join(save_path, filename)
        os.makedirs(save_path, exist_ok=True)
        
        # Fase 3: Recibir y escribir bloques en streaming
        total_bytes_received = self._receive_streaming_blocks(file_path, block_count)
        
        # Fase 4: Verificación final
        response = NetworkUtils.receive_response(self.client.socket)
        
        if response == Response.DOWNLOAD_COMPLETE:
            logger.log("DOWNLOAD", f"Descarga completada: {filename} - {total_bytes_received} bytes recibidos")
            return True
        else:
            logger.log("DOWNLOAD", f"Error en descarga: {response}")
            return False

    def _receive_streaming_metadata(self):
        """Recibe metadatos del streaming del servidor"""
        # Recibir nombre del archivo
        filename = NetworkUtils.receive_filename(self.client.socket)
        
        # Recibir cantidad de bloques
        block_count = int.from_bytes(self.client.socket.recv(4), 'big')
        
        return filename, block_count

    def _receive_streaming_blocks(self, file_path: str, block_count: int):
        """Recibe y escribe todos los bloques en streaming"""
        total_bytes_received = 0
        
        with open(file_path, 'wb') as output_file:
            for block_index in range(block_count):
                bytes_received = self._receive_single_block(output_file, block_index, block_count)
                total_bytes_received += bytes_received
        
        return total_bytes_received

    def _receive_single_block(self, output_file, block_index: int, total_blocks: int):
        """Recibe un solo bloque y lo escribe en el archivo"""
        # Recibir tamaño del bloque
        block_size = int.from_bytes(self.client.socket.recv(8), 'big')
        
        if block_size == 0:
            logger.log("ERROR", f"Bloque {block_index+1} faltante en el servidor")
            return 0
        
        # Recibir y escribir contenido del bloque
        bytes_received = 0
        while bytes_received < block_size:
            chunk_size = min(self.client.BUFFER_SIZE, block_size - bytes_received)
            chunk = self.client.socket.recv(chunk_size)
            if not chunk:
                break
            output_file.write(chunk)
            bytes_received += len(chunk)
        
        logger.log("DOWNLOAD", f"Bloque {block_index+1}/{total_blocks} recibido: {bytes_received} bytes")
        return bytes_received