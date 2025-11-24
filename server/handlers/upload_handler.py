import os
import socket
import threading
from core.protocol import Response
from core.logger import logger

class UploadHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente en streaming"""
        try:
            # Fase 1: Recepción de metadatos
            filename = self.server._receive_filename(client)
            file_size = self.server._receive_file_size(client)
            
            # Fase 2: Verificación de existencia (con lock)
            with self.server.file_table_lock:
                if self.server.file_table.get_info_file(filename):
                    client.send(Response.FILE_ALREADY_EXISTS.to_bytes())
                    return None
            
            # Fase 3: Verificación de espacio disponible (con lock)
            required_blocks = (file_size + self.server.BLOCK_SIZE - 1) // self.server.BLOCK_SIZE
            with self.server.block_table_lock:
                if not self.server.block_table.has_available_blocks(required_blocks):
                    logger.log("UPLOAD", f"Espacio insuficiente: {filename} requiere {required_blocks} bloques")
                    client.send(Response.STORAGE_FULL.to_bytes())
                    return None

            # Fase 4: Confirmación para cargar el archivo
            client.send(Response.SUCCESS.to_bytes())
            
            # Fase 5: Procesamiento en streaming (con locks para asignación)
            with self.server.file_operation_lock:
                with self.server.file_table_lock, self.server.block_table_lock:
                    file_id = self.server.file_table.create_file(filename, file_size)
                    allocated_blocks = self.server.block_table.allocate_blocks(required_blocks, [0])
                    self.server.file_table.set_first_block(file_id, allocated_blocks[0])
                    self.server.file_table.update_block_count(file_id, required_blocks)
            
            # Fase 6: Crear bloques físicos (sin lock, solo I/O)
            blocks_info = self._process_streaming_upload(client, filename, file_id, file_size, required_blocks)
            
            # Fase 7: Confirmación al cliente
            client.send(Response.UPLOAD_COMPLETE.to_bytes())
            logger.log("UPLOAD", f"Upload completado - FileID: {file_id}, Bloques: {len(blocks_info['blocks'])}")
            return blocks_info
        
        except Exception as e:
            logger.log("UPLOAD", f"Error durante upload: {str(e)}")
            client.send(Response.SERVER_ERROR.to_bytes())
            return None

    def _process_streaming_upload(self, client: socket.socket, filename: str, file_id: int, file_size: int, required_blocks: int):
        """Procesa la subida en streaming y crea los bloques directamente"""
        logger.log("UPLOAD", f"Procesando upload en streaming: {filename} ({file_size} bytes, {required_blocks} bloques)")
        
        # Crear directorio para bloques físicos
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.server.block_dir, sub_dir)
        os.makedirs(blocks_dir, exist_ok=True)
        
        blocks_created = []
        bytes_remaining = file_size
        block_index = 0
        
        # Procesar archivo en bloques directamente del stream
        while bytes_remaining > 0 and block_index < required_blocks:
            block_name = f"block_{block_index}.bin"
            block_path = os.path.join(blocks_dir, block_name)
            
            # Calcular tamaño del bloque actual
            current_block_size = min(self.server.BLOCK_SIZE, bytes_remaining)
            
            # Crear bloque físico desde el stream
            self._create_block_from_stream(client, block_path, current_block_size)
            blocks_created.append(block_name)
            
            bytes_remaining -= current_block_size
            block_index += 1
            
            # Mostrar progreso
            mb_processed = (block_index * self.server.BLOCK_SIZE) / (1024 * 1024)
            mb_total = file_size / (1024 * 1024)
            logger.log("UPLOAD", f"Progreso: {mb_processed:.1f} / {mb_total:.1f} MB - Bloque {block_index}/{required_blocks}")
        
        logger.log("UPLOAD", f"Bloques creados: {len(blocks_created)}")
        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks_created,
            'blocks_dir': blocks_dir
        }

    def _create_block_from_stream(self, client: socket.socket, block_path: str, block_size: int):
        """Crea un bloque físico directamente desde el stream del cliente"""
        with open(block_path, 'wb') as block_file:
            bytes_received = 0
            while bytes_received < block_size:
                chunk_size = min(self.server.BUFFER_SIZE, block_size - bytes_received)
                chunk = client.recv(chunk_size)
                if not chunk:
                    break
                block_file.write(chunk)
                bytes_received += len(chunk)