import os
import socket
import shutil
import json
from core.protocol import Response
from core.logger import logger
from server.block_table import BlockTable
from server.file_table import FileTable

class FileServer:
    def __init__(self, capacity_mb: int = 1000, block_dir: str = "blocks", temp_dir: str = "temp", 
                 buffer_size: int = 4096, data_dir: str = "data"):
        # =========================================================================
        # CONFIGURACIÓN INICIAL DEL SERVIDOR
        # =========================================================================
        self.capacity_mb = capacity_mb
        self.block_dir = block_dir
        self.temp_dir = temp_dir
        self.data_dir = data_dir
        self.BUFFER_SIZE = buffer_size
        self.BLOCK_SIZE = 1024 * 1024  # 1MB por bloque
        
        # Crear directorios necesarios para operación
        os.makedirs(block_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Inicializar tablas de gestión
        total_blocks = capacity_mb
        self.block_table = BlockTable(total_blocks=total_blocks, data_dir=data_dir)
        self.file_table = FileTable(data_dir=data_dir)
        
        logger.log("SERVER", f"Servidor de archivos listo - {total_blocks} bloques disponibles")
        logger.log("SERVER", f"Archivos registrados: {len(self.file_table.files)}")

    # =========================================================================
    # MÉTODOS PRINCIPALES DE PROCESAMIENTO DE SOLICITUDES
    # =========================================================================

    def process_upload_request(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente en streaming"""
        try:
            # Fase 1: Recepción de metadatos
            filename = self._receive_filename(client)
            file_size = self._receive_file_size(client)
            
            # Fase 2: Verificación de existencia
            if self.file_table.get_info_file(filename):
                client.send(Response.FILE_ALREADY_EXISTS.to_bytes())
                return None
            
            # Fase 3: Verificación de espacio disponible
            required_blocks = (file_size + self.BLOCK_SIZE - 1) // self.BLOCK_SIZE
            if not self.block_table.has_available_blocks(required_blocks):
                logger.log("UPLOAD", f"Espacio insuficiente: {filename} requiere {required_blocks} bloques")
                client.send(Response.STORAGE_FULL.to_bytes())
                return None

            # Fase 4: Confirmación para cargar el archivo
            client.send(Response.SUCCESS.to_bytes())
            
            # Fase 5: Procesamiento en streaming
            file_id = self.file_table.create_file(filename, file_size)
            blocks_info = self._process_streaming_upload(client, filename, file_id, file_size, required_blocks)
            
            # Fase 6: Confirmación al cliente
            client.send(Response.UPLOAD_COMPLETE.to_bytes())
            logger.log("UPLOAD", f"Upload completado - FileID: {file_id}, Bloques: {len(blocks_info['blocks'])}")
            return blocks_info
        
        except Exception as e:
            logger.log("UPLOAD", f"Error durante upload: {str(e)}")
            client.send(Response.SERVER_ERROR.to_bytes())
            return None

    def process_download_request(self, client: socket.socket):
        """Procesa una solicitud de download del cliente en streaming"""
        try:
            # Fase 1: Verificación de existencia
            filename = self._receive_filename(client)
            file_info = self.file_table.get_info_file(filename)
            
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

    def process_delete_request(self, client: socket.socket):
        """Procesa una solicitud de eliminación de archivo"""
        try:
            # Fase 1: Verificación de existencia
            filename = self._receive_filename(client)
            file_info = self.file_table.get_info_file(filename)
            
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            # Fase 2: Eliminación lógica y física
            self._delete_file(filename, file_info)
            client.send(Response.DELETE_COMPLETE.to_bytes())
            logger.log("DELETE", f"Archivo eliminado: {filename}")

        except Exception as e:
            logger.log("DELETE", f'Error durante eliminación: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_list_request(self, client: socket.socket):
        """Procesa una solicitud de listado de archivos"""
        try:
            # Recopilar información de todos los archivos
            files_info = self._get_all_files_info()
            
            # Serializar y enviar respuesta
            files_json = json.dumps(files_info).encode('utf-8')
            client.send(len(files_json).to_bytes(4, 'big'))
            client.send(files_json)
            
            logger.log("LIST", f"Listado enviado - {len(files_info)} archivos")
            
        except Exception as e:
            logger.log("LIST", f'Error durante listado: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_info_request(self, client: socket.socket):
        """Procesa solicitud de información de archivo"""
        try:
            # Fase 1: Obtención de información
            filename = self._receive_filename(client)
            file_info = self.get_file_info(filename)
            
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return
            
            # Fase 2: Preparación y envío de respuesta
            serializable_info = self._prepare_file_info_for_serialization(file_info)
            self._send_json_response(client, serializable_info)
            
        except Exception as e:
            logger.log("INFO", f'Error durante info: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_storage_status_request(self, client: socket.socket):
        """Procesa solicitud de estado del almacenamiento"""
        try:
            # Obtener y enviar estado del sistema
            status = self.get_storage_status()
            self._send_json_response(client, status)
            
        except Exception as e:
            logger.log("STATUS", f'Error durante storage status: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    # =========================================================================
    # MANEJO DE COMUNICACIÓN CON EL CLIENTE
    # =========================================================================

    def _receive_filename(self, client: socket.socket) -> str:
        """Recibe el nombre de archivo del cliente"""
        filename_size = int.from_bytes(client.recv(4), 'big')
        filename_bytes = client.recv(filename_size)
        return filename_bytes.decode('utf-8')

    def _receive_file_size(self, client: socket.socket) -> int:
        """Recibe el tamaño del archivo"""
        file_size_bytes = client.recv(8)
        return int.from_bytes(file_size_bytes, 'big')

    def _send_json_response(self, client: socket.socket, data: dict):
        """Envía una respuesta JSON al cliente"""
        data_json = json.dumps(data).encode('utf-8')
        client.send(len(data_json).to_bytes(4, 'big'))
        client.send(data_json)

    # =========================================================================
    # GESTIÓN DE BLOQUES EN STREAMING
    # =========================================================================

    def _process_streaming_upload(self, client: socket.socket, filename: str, file_id: int, file_size: int, required_blocks: int):
        """Procesa la subida en streaming y crea los bloques directamente"""
        logger.log("UPLOAD", f"Procesando upload en streaming: {filename} ({file_size} bytes, {required_blocks} bloques)")
        
        # Asignar bloques lógicos
        allocated_blocks = self.block_table.allocate_blocks(file_id, required_blocks)
        self.file_table.set_first_block(file_id, allocated_blocks[0])
        self.file_table.update_block_count(file_id, required_blocks)
        
        # Crear directorio para bloques físicos
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        os.makedirs(blocks_dir, exist_ok=True)
        
        blocks_created = []
        bytes_remaining = file_size
        block_index = 0
        
        # Procesar archivo en bloques directamente del stream
        while bytes_remaining > 0 and block_index < required_blocks:
            block_name = f"block_{block_index}.bin"
            block_path = os.path.join(blocks_dir, block_name)
            
            # Calcular tamaño del bloque actual
            current_block_size = min(self.BLOCK_SIZE, bytes_remaining)
            
            # Crear bloque físico desde el stream
            self._create_block_from_stream(client, block_path, current_block_size)
            blocks_created.append(block_name)
            
            bytes_remaining -= current_block_size
            block_index += 1
            
            # Mostrar progreso
            mb_processed = (block_index * self.BLOCK_SIZE) / (1024 * 1024)
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
                chunk_size = min(self.BUFFER_SIZE, block_size - bytes_received)
                chunk = client.recv(chunk_size)
                if not chunk:
                    break
                block_file.write(chunk)
                bytes_received += len(chunk)

    def _stream_file_to_client(self, client: socket.socket, filename: str, file_info: dict):
        """Envía el archivo al cliente en streaming desde los bloques"""
        # Obtener cadena de bloques lógicos
        block_chain = self.block_table.get_block_chain(file_info["first_block_id"])
        
        if not block_chain:
            logger.log("DOWNLOAD", f'Cadena de bloques vacía para: {filename}')
            return

        # Preparar información de bloques físicos
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        
        if not os.path.exists(blocks_dir):
            logger.log("ERROR", f'Directorio de bloques no encontrado: {blocks_dir}')
            return

        # Obtener bloques físicos ordenados
        block_files = self._get_physical_blocks(blocks_dir)
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
                chunk = block_file.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                client.send(chunk)
                bytes_sent += len(chunk)
        
        logger.log("DOWNLOAD", f"Bloque {block_index+1}/{total_blocks} transmitido: {os.path.basename(block_path)} - {block_size} bytes")

    # =========================================================================
    # MÉTODOS AUXILIARES (sin cambios)
    # =========================================================================

    def _get_physical_blocks(self, blocks_dir: str) -> list:
        """Obtiene la lista de bloques físicos ordenados"""
        if not os.path.exists(blocks_dir):
            return []

        all_files = os.listdir(blocks_dir)
        block_files = [f for f in all_files if f.endswith('.bin')]
        
        # Ordenar por número de bloque: block_0.bin, block_1.bin, etc.
        block_files = sorted(block_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        return block_files

    def _delete_file(self, filename: str, file_info: dict):
        """Elimina completamente un archivo del sistema"""
        file_id = self.file_table.name_to_id[filename]

        # Liberar bloques lógicos
        blocks_freed = self._free_logical_blocks(file_info)
        
        # Eliminar de FileTable
        self.file_table.delete_file(file_id)

        # Eliminar archivos físicos
        self._delete_physical_blocks(filename)
        
        logger.log("DELETE", f"Archivo eliminado: {filename} (bloques liberados: {blocks_freed})")

    def _free_logical_blocks(self, file_info: dict) -> int:
        """Libera los bloques lógicos asignados al archivo"""
        if file_info["first_block_id"] is not None:
            return self.block_table.free_blocks(file_info["first_block_id"])
        return 0

    def _delete_physical_blocks(self, filename: str):
        """Elimina los archivos físicos del archivo"""
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        
        if os.path.exists(blocks_dir):
            shutil.rmtree(blocks_dir)
            logger.log("DELETE", f"Directorio eliminado: {blocks_dir}")

    def _get_all_files_info(self) -> list:
        """Obtiene información de todos los archivos registrados"""
        files_info = []
        for file_id, file_info in self.file_table.files.items():
            files_info.append({
                'filename': file_info['filename'],
                'size': file_info['total_size'],
                'created_at': file_info['created_at'].isoformat(),
                'blocks': file_info['block_count']
            })
        return files_info

    def _prepare_file_info_for_serialization(self, file_info: dict) -> dict:
        """Prepara la información del archivo para serialización JSON"""
        serializable_info = file_info.copy()
        serializable_info['created_at'] = file_info['created_at'].isoformat()
        return serializable_info

    def get_storage_status(self):
        """Obtiene el estado completo del almacenamiento"""
        block_status = self.block_table.get_system_status()
        
        return {
            "total_blocks": block_status["total_blocks"],
            "used_blocks": block_status["used_blocks"],
            "free_blocks": block_status["free_blocks"],
            "usage_percent": block_status["usage_percent"],
            "file_count": len(self.file_table.files),
            "total_files_size": sum(file_info["total_size"] for file_info in self.file_table.files.values())
        }

    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo específico"""
        file_info = self.file_table.get_info_file(filename)
        if not file_info:
            return None

        # Obtener cadena de bloques
        block_chain = []
        if file_info["first_block_id"] is not None:
            block_chain = self.block_table.get_block_chain(file_info["first_block_id"])

        return {
            "filename": file_info["filename"],
            "size": file_info["total_size"],
            "created_at": file_info["created_at"],
            "block_count": file_info["block_count"],
            "first_block_id": file_info["first_block_id"],
            "block_chain": block_chain
        }

    def cleanup(self):
        """Limpia recursos (para shutdown ordenado)"""
        logger.log("SERVER", "Cerrando servidor de archivos...")
        logger.log("SERVER", "Estado guardado correctamente")