import os
import socket
from core.protocol import Response
from core.logger import logger

class DownloadHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de download del cliente en streaming"""
        try:
            # Fase 1: Verificación de existencia (con lock)
            filename = self.server._receive_filename(client)
            with self.server.file_table_lock:
                file_info = self.server.file_table.get_info_file(filename)
                
            if not file_info:
                logger.log("DOWNLOAD", f'Archivo no encontrado: {filename}')
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            # Fase 2: Envío del archivo en streaming
            client.send(Response.SUCCESS.to_bytes())
            self._stream_file_to_client(client, filename, file_info)
            client.send(Response.DOWNLOAD_COMPLETE.to_bytes())

        except Exception as e:
            logger.log("DOWNLOAD", f'Error durante descarga: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _stream_file_to_client(self, client: socket.socket, filename: str, file_info):
        """Envía el archivo al cliente en streaming desde los bloques"""
        # Obtener cadena de bloques lógicos (con lock)
        with self.server.block_table_lock:
            block_chain = self.server.block_table.get_block_chain(file_info.first_block_id)
        
        if not block_chain:
            logger.log("DOWNLOAD", f'Cadena de bloques vacía para: {filename}')
            return

        # Preparar información de bloques físicos
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.server.block_dir, sub_dir)
        
        if not os.path.exists(blocks_dir):
            logger.log("ERROR", f'Directorio de bloques no encontrado: {blocks_dir}')
            return

        # Obtener bloques físicos ordenados
        block_files = self.server._get_physical_blocks(blocks_dir)
        if not block_files:
            logger.log("ERROR", f"No hay bloques físicos en: {blocks_dir}")
            return

        # Enviar metadatos de streaming
        self._send_streaming_metadata(client, filename, len(block_files))
        
        # Enviar bloques en streaming
        self._stream_blocks_to_client(client, blocks_dir, block_files)
        
        logger.log("DOWNLOAD", f'Streaming completado: {filename} - {len(block_files)} bloques')

    def _send_streaming_metadata(self, client: socket.socket, filename: str, block_count: int):
        """Envía metadatos para el streaming"""
        # Enviar nombre del archivo
        filename_bytes = filename.encode('utf-8')
        client.send(len(filename_bytes).to_bytes(4, 'big'))
        client.send(filename_bytes)
        
        # Enviar cantidad de bloques
        client.send(block_count.to_bytes(4, 'big'))

    def _stream_blocks_to_client(self, client: socket.socket, blocks_dir: str, block_files: list):
        """Transmite todos los bloques al cliente en streaming"""
        for i, block_name in enumerate(block_files):
            block_path = os.path.join(blocks_dir, block_name)
            self._stream_single_block(client, block_path, i, len(block_files))

    def _stream_single_block(self, client: socket.socket, block_path: str, block_index: int, total_blocks: int):
        """Transmite un solo bloque al cliente"""
        if not os.path.exists(block_path):
            logger.log("ERROR", f"Bloque no encontrado: {block_path}")
            client.send((0).to_bytes(8, 'big'))
            return

        block_size = os.path.getsize(block_path)
        client.send(block_size.to_bytes(8, 'big'))
        
        # Transmitir contenido del bloque
        with open(block_path, 'rb') as block_file:
            bytes_sent = 0
            while bytes_sent < block_size:
                chunk = block_file.read(self.server.BUFFER_SIZE)
                if not chunk:
                    break
                client.send(chunk)
                bytes_sent += len(chunk)
        
        logger.log("DOWNLOAD", f"Bloque {block_index+1}/{total_blocks} transmitido: {os.path.basename(block_path)} - {block_size} bytes")