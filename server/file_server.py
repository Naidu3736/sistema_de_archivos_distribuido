import os
import socket
import shutil
import json
from core.split_union import split
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
        self.BLOCK_SIZE = 1024 * 1024
        
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
        """Procesa una solicitud de upload del cliente"""
        try:
            # Fase 1: Recepción del archivo temporal
            file_metadata = self._receive_temp_file(client)

            if not file_metadata:
                logger.log("UPLOAD", "El archivo excede la capacidad actual del sistema")
                client.send(Response.STORAGE_FULL.to_bytes())
                return None
            
            client.send(Response.SUCCESS.to_bytes())
            filename, file_size, temp_file_path = file_metadata
            
            # Fase 2: Verificación de existencia
            if self.file_table.get_info_file(filename):
                client.send(Response.FILE_ALREADY_EXISTS.to_bytes())
                self._cleanup_temp_file(temp_file_path)
                return None
            
            # Fase 3: Procesamiento y almacenamiento
            file_id = self.file_table.create_file(filename, file_size)
            blocks_info = self._process_file_blocks(temp_file_path, file_id)
            self._cleanup_temp_file(temp_file_path)
            
            # Fase 4: Confirmación al cliente
            client.send(Response.UPLOAD_COMPLETE.to_bytes())
            logger.log("UPLOAD", f"Upload completado - FileID: {file_id}, Bloques: {len(blocks_info['blocks'])}")
            return blocks_info
        
        except Exception as e:
            logger.log("UPLOAD", f"Error durante upload: {str(e)}")
            client.send(Response.SERVER_ERROR.to_bytes())
            return None

    def process_download_request(self, client: socket.socket):
        """Procesa una solicitud de download del cliente"""
        try:
            # Fase 1: Verificación de existencia
            filename = self._receive_filename(client)
            file_info = self.file_table.get_info_file(filename)
            
            if not file_info:
                logger.log("DOWNLOAD", f'Archivo no encontrado: {filename}')
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            # Fase 2: Envío del archivo
            client.send(Response.SUCCESS.to_bytes())
            self._send_file_to_client(client, filename, file_info)
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
            
            logger.log("LIST", f"Listado enviado - {len(files_info)}")
            
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

    def _receive_temp_file(self, client: socket.socket):
        """
        Recibe un archivo completo del cliente y lo guarda temporalmente
        Retorna: (filename, file_size, temp_file_path)
        """
        logger.log("SERVER", "Recibiendo información del archivo...")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Recepción de metadatos
        filename = self._receive_file_metadata(client)
        file_size = self._receive_file_size(client)
        
        import math
        required_blocks = math.ceil(file_size / self.BLOCK_SIZE)
        if not self.block_table.has_available_blocks(required_blocks):
            logger.log("UPLOAD", f"No hay bloques suficientes. Requeridos: {required_blocks}, Disponibles: {len(self.block_table.available_blocks)}")
            return None

        logger.log("SERVER", f'Recibiendo: {filename} ({file_size} bytes)')

        # Recepción del contenido
        temp_file_path = self._receive_file_content(client, filename, file_size)
        
        return filename, file_size, temp_file_path

    def _receive_file_metadata(self, client: socket.socket) -> str:
        """Recibe los metadatos del archivo (nombre)"""
        size_bytes = client.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        file_bytes = client.recv(size)
        return file_bytes.decode('utf-8')

    def _receive_file_size(self, client: socket.socket) -> int:
        """Recibe el tamaño del archivo"""
        file_size_bytes = client.recv(8)
        return int.from_bytes(file_size_bytes, 'big')

    def _receive_file_content(self, client: socket.socket, filename: str, file_size: int) -> str:
        """Recibe el contenido del archivo y lo guarda en temporal"""
        temp_file_path = os.path.join(self.temp_dir, filename)

        
        with open(temp_file_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                chunk = client.recv(min(self.BUFFER_SIZE, file_size - bytes_received))
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)

                # Mostrar progreso cada 1MB
                self._show_download_progress(bytes_received, file_size)

        logger.log("SERVER", f"Recepción completada: {os.path.basename(temp_file_path)}")
        return temp_file_path

    def _show_download_progress(self, bytes_received: int, total_size: int):
        """Muestra el progreso de descarga cada 1MB"""
        if bytes_received % self.BLOCK_SIZE == 0 or bytes_received == total_size:
            mb_received = bytes_received / self.BLOCK_SIZE
            mb_total = total_size / self.BLOCK_SIZE
            logger.log("SERVER", f"Progreso: {mb_received:.1f} / {mb_total:.1f} MB")

    def _send_json_response(self, client: socket.socket, data: dict):
        """Envía una respuesta JSON al cliente"""
        data_json = json.dumps(data).encode('utf-8')
        client.send(len(data_json).to_bytes(4, 'big'))
        client.send(data_json)

    # =========================================================================
    # GESTIÓN DE BLOQUES DE ARCHIVOS
    # =========================================================================

    def _process_file_blocks(self, file_path: str, file_id: int) -> dict:
        """
        Procesa la división y asignación de bloques de un archivo
        Retorna información sobre los bloques creados
        """
        filename = os.path.basename(file_path)
        logger.log("BLOCKS", f"Dividiendo archivo en bloques: {filename}")

        # División física del archivo
        blocks_info = self._split_into_blocks(file_path)
        num_blocks = len(blocks_info['blocks'])

        # Asignación lógica de bloques
        allocated_blocks = self.block_table.allocate_blocks(file_id, num_blocks)
        
        # Actualización de metadatos
        self._update_file_table_blocks(file_id, allocated_blocks, num_blocks)
        
        return blocks_info

    def _split_into_blocks(self, file_path: str) -> dict:
        """Divide el archivo en bloques físicos"""
        filename = os.path.basename(file_path)
        sub_dir = os.path.splitext(filename)[0]
        sub_dir_path = os.path.join(self.block_dir, sub_dir)

        # Usar función split que crea block_0.bin, block_1.bin, etc.
        blocks = split(file_path, sub_dir_path)
        logger.log("BLOCKS", f'División completada: {len(blocks)} bloques creados')
        
        # VERIFICACIÓN: Confirmar que los bloques se crearon físicamente
        self._verify_blocks_creation(sub_dir_path)
        
        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks,
            'blocks_dir': sub_dir_path
        }

    def _verify_blocks_creation(self, blocks_dir: str):
        """Verifica que los bloques se hayan creado correctamente"""
        if os.path.exists(blocks_dir):
            created_files = os.listdir(blocks_dir)
            logger.log("DEBUG", f"Archivos creados en {blocks_dir}: {created_files}")
        else:
            logger.log("ERROR", f"No se creó el directorio: {blocks_dir}")

    def _update_file_table_blocks(self, file_id: int, allocated_blocks: list, num_blocks: int):
        """Actualiza la información de bloques en FileTable"""
        if allocated_blocks:
            self.file_table.set_first_block(file_id, allocated_blocks[0])
            self.file_table.update_block_count(file_id, num_blocks)
            logger.log("BLOCKS", f"Bloques lógicos asignados: {allocated_blocks}")

    # =========================================================================
    # GESTIÓN OF DESCARGA Y ENVÍO DE ARCHIVOS
    # =========================================================================

    def _send_file_to_client(self, client: socket.socket, filename: str, file_info: dict):
        """Coordina el envío de un archivo al cliente"""
        # Obtener cadena de bloques lógicos
        block_chain = self.block_table.get_block_chain(file_info["first_block_id"])
        
        if not block_chain:
            logger.log("DOWNLOAD", f'Cadena de bloques vacía para: {filename}')
            return

        # Preparar información de bloques físicos
        blocks_info = self._prepare_blocks_info(filename, file_info, block_chain)
        if not blocks_info:
            return

        # Enviar bloques al cliente
        self._send_blocks_to_client(client, blocks_info)
        logger.log("DOWNLOAD", f'Descarga completada: {filename}')

    def _prepare_blocks_info(self, filename: str, file_info: dict, block_chain: list) -> dict:
        """Prepara la información de bloques físicos para envío"""
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        
        # Verificar existencia del directorio
        if not os.path.exists(blocks_dir):
            logger.log("ERROR", f'Directorio de bloques no encontrado: {blocks_dir}')
            return None

        # Obtener lista de bloques físicos reales
        block_files = self._get_physical_blocks(blocks_dir)
        if not block_files:
            logger.log("ERROR", f"No hay bloques físicos en: {blocks_dir}")
            return None

        # Validar cantidad de bloques
        self._validate_block_count(block_files, file_info["block_count"])

        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': block_files,
            'blocks_dir': blocks_dir
        }

    def _get_physical_blocks(self, blocks_dir: str) -> list:
        """Obtiene la lista de bloques físicos ordenados"""
        if not os.path.exists(blocks_dir):
            return []

        all_files = os.listdir(blocks_dir)
        block_files = [f for f in all_files if f.endswith('.bin')]
        
        # Ordenar por número de bloque: block_0.bin, block_1.bin, etc.
        block_files = sorted(block_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        return block_files

    def _validate_block_count(self, actual_blocks: list, expected_count: int):
        """Valida que la cantidad de bloques físicos coincida con la esperada"""
        if len(actual_blocks) != expected_count:
            logger.log("WARNING", f"Se esperaban {expected_count} bloques, pero hay {len(actual_blocks)} físicos")

    def _send_blocks_to_client(self, client: socket.socket, blocks_info: dict):
        """Envía todos los bloques al cliente en secuencia"""
        # Envío de metadatos
        self._send_blocks_metadata(client, blocks_info)
        
        # Envío de contenido de bloques
        self._send_blocks_content(client, blocks_info)

    def _send_blocks_metadata(self, client: socket.socket, blocks_info: dict):
        """Envía los metadatos de los bloques al cliente"""
        # Enviar nombre del subdirectorio
        sub_dir_bytes = blocks_info['sub_dir'].encode('utf-8')
        client.send(len(sub_dir_bytes).to_bytes(4, 'big'))
        client.send(sub_dir_bytes)

        # Enviar nombre del archivo
        filename_bytes = blocks_info['filename'].encode('utf-8')
        client.send(len(filename_bytes).to_bytes(4, 'big'))
        client.send(filename_bytes)

        # Enviar cantidad de bloques
        client.send(len(blocks_info['blocks']).to_bytes(4, 'big'))

        # Enviar nombres de bloques individuales
        for block in blocks_info['blocks']:
            block_name_bytes = block.encode('utf-8')
            client.send(len(block_name_bytes).to_bytes(4, 'big'))
            client.send(block_name_bytes)

    def _send_blocks_content(self, client: socket.socket, blocks_info: dict):
        """Envía el contenido de todos los bloques"""
        for i, block in enumerate(blocks_info['blocks']):
            self._send_single_block(client, block, blocks_info['blocks_dir'])
            logger.log("DOWNLOAD", f"Bloque {i+1}/{len(blocks_info['blocks'])} enviado: {block}")

    def _send_single_block(self, client: socket.socket, block_name: str, blocks_dir: str):
        """Envía un solo bloque al cliente"""
        block_path = os.path.join(blocks_dir, block_name)
        
        # Verificar existencia del bloque
        if not os.path.exists(block_path):
            logger.log("ERROR", f"Bloque no encontrado: {block_path}")
            client.send((0).to_bytes(8, 'big'))  # Indicar bloque faltante
            return

        # Enviar tamaño y contenido del bloque
        block_size = os.path.getsize(block_path)
        client.send(block_size.to_bytes(8, 'big'))

        self._send_block_content(client, block_path, block_size)
        # logger.log("DOWNLOAD", f"  {block_name} enviado ({block_size} bytes)")

    def _send_block_content(self, client: socket.socket, block_path: str, block_size: int):
        """Envía el contenido de un bloque específico"""
        with open(block_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < block_size:
                chunk = f.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                client.send(chunk)
                bytes_sent += len(chunk)

    # =========================================================================
    # GESTIÓN DE ELIMINACIÓN Y LIMPIEZA
    # =========================================================================

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

    def _cleanup_temp_file(self, temp_file_path):
        """Elimina archivo temporal"""
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.log("CLEANUP", f"Archivo temporal eliminado: {temp_file_path}")
        except Exception as e:
            logger.log("ERROR", f"Error limpiando archivo temporal: {str(e)}")

    # =========================================================================
    # CONSULTAS E INFORMACIÓN DEL SISTEMA
    # =========================================================================

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