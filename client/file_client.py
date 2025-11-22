import socket
import os
import json
from core.protocol import Command, Response
from core.split_union import union, clean_blocks
from core.logger import logger

class FileClient:
    def __init__(self, host_server: str = "0.0.0.0", port_server: int = 8001, buffer_size: int = 4096):
        # =========================================================================
        # CONFIGURACIÓN INICIAL DEL CLIENTE
        # =========================================================================
        self.host_server = host_server
        self.port_server = port_server
        self.BUFFER_SIZE = buffer_size
        self.temp_dir = "temp"
        self.socket = None
        self.is_connected = False  # Nuevo: estado de conexión
        
        # Crear directorio temporal para operaciones
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.log("CLIENT", f"Cliente de archivos configurado - Servidor: {host_server}:{port_server}")
    
    # =========================================================================
    # GESTIÓN DE CONEXIÓN Y DESCONEXIÓN MEJORADA
    # =========================================================================

    def connect(self):
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
            self.socket.send(Command.DISCONNECT.to_bytes())
            self.socket.close()
            self.socket = None
            self.is_connected = False
            logger.log("CLIENT", "Desconectado del servidor")

    def ensure_connection(self):
        """Verifica y mantiene la conexión activa"""
        if not self.is_connected or not self.socket:
            return self.connect()
        
        # Verificar si el socket sigue activo
        try:
            # Intentar una operación de prueba no bloqueante
            self.socket.settimeout(0.1)
            data = self.socket.recv(1, socket.MSG_PEEK)
            return True
        except (socket.timeout, socket.error):
            # Reconectar si hay problemas
            self.disconnect()
            return self.connect()
        finally:
            self.socket.settimeout(None)

    # =========================================================================
    # OPERACIONES PRINCIPALES CON ARCHIVOS (CONEXIÓN PERSISTENTE)
    # =========================================================================

    def upload_file(self, file_path: str):
        """Sube un archivo al sistema distribuido de archivos"""
        if not self.ensure_connection():
            return False
        
        if not self._validate_local_file(file_path):
            return False
            
        try:
            logger.log("UPLOAD", "Iniciando subida de archivo...")
            
            # Fase 1: Envío de comando y metadatos
            self._send_command(Command.UPLOAD)
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.log("UPLOAD", f"Subiendo archivo: {filename} ({file_size} bytes)")
            self._send_file_metadata(filename, file_size)
            
            # Fase 2: Envío del contenido
            self._send_file_content(file_path, file_size)
        
            # Fase 3: Verificación de respuesta
            return self._handle_upload_response(filename)
        
        except Exception as e:
            logger.log("UPLOAD", f"Error durante subida: {str(e)}")
            self.disconnect()  # Solo desconectar en error
            return False

    def download_file(self, filename: str, save_path: str):
        """Descarga un archivo del sistema distribuido de archivos"""
        if not self.ensure_connection():
            return False
            
        try:
            logger.log("DOWNLOAD", f"Solicitando descarga: {filename}")
            
            # Fase 1: Solicitud de descarga
            self._send_command(Command.DOWNLOAD)
            self._send_filename(filename)
            
            # Fase 2: Verificación de disponibilidad
            if not self._validate_download_availability(filename):
                return False
            
            # Fase 3: Recepción y reconstrucción
            logger.log("DOWNLOAD", "Preparando recepción de bloques...")
            blocks_info = self._receive_blocks_from_server()
            
            # Fase 4: Procesamiento del archivo
            success = self._process_downloaded_blocks(blocks_info, save_path, filename)
            
            # NO desconectar aquí - mantener conexión
            return success
            
        except Exception as e:
            logger.log("DOWNLOAD", f"Error durante descarga: {str(e)}")
            self.disconnect()
            return False

    def delete_file(self, filename: str):
        """Elimina un archivo del sistema distribuido de archivos"""
        if not self.ensure_connection():
            return False
            
        try:
            logger.log("DELETE", f"Solicitando eliminación: {filename}")
            
            # Fase 1: Envío de solicitud
            self._send_command(Command.DELETE)
            self._send_filename(filename)
            
            # Fase 2: Procesamiento de respuesta
            response = self._receive_response()
            
            if response == Response.DELETE_COMPLETE:
                logger.log("DELETE", f"Archivo eliminado: {filename}")
                # NO desconectar aquí
                return True
            elif response == Response.FILE_NOT_FOUND:
                logger.log("DELETE", f"Archivo no encontrado: {filename}")
                # NO desconectar aquí
                return False
            else:
                logger.log("DELETE", f"Error en eliminación: {response}")
                # NO desconectar aquí
                return False
            
        except Exception as e:
            logger.log("DELETE", f"Error durante eliminación: {str(e)}")
            self.disconnect()
            return False

    # =========================================================================
    # OPERACIONES DE CONSULTA E INFORMACIÓN (CONEXIÓN PERSISTENTE)
    # =========================================================================

    def list_files(self):
        """Solicita lista de archivos disponibles en el servidor"""
        if not self.ensure_connection():
            return []
            
        try:
            logger.log("LIST", "Solicitando lista de archivos...")
            
            # Fase 1: Envío de comando
            self._send_command(Command.LIST_FILES)
            
            # Fase 2: Recepción y procesamiento de datos
            files_info = self._receive_json_response()
            
            logger.log("LIST", f"Lista de archivos recibida: {len(files_info)} archivos")
            # NO desconectar aquí - mantener conexión
            return files_info
            
        except Exception as e:
            logger.log("LIST", f"Error obteniendo lista de archivos: {str(e)}")
            self.disconnect()
            return []

    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo específico"""
        if not self.ensure_connection():
            return None
            
        try:
            logger.log("INFO", f"Solicitando información de: {filename}")
            
            # Fase 1: Envío de solicitud
            self._send_command(Command.FILE_INFO)
            self._send_filename(filename)
            
            # Fase 2: Recepción de información
            file_info = self._receive_json_response()
            
            # NO desconectar aquí - mantener conexión
            return file_info
            
        except Exception as e:
            logger.log("INFO", f"Error obteniendo información del archivo: {str(e)}")
            self.disconnect()
            return None

    def get_storage_status(self):
        """Obtiene el estado del almacenamiento del servidor"""
        if not self.ensure_connection():
            return None
            
        try:
            logger.log("STATUS", "Solicitando estado del almacenamiento...")
            
            # Fase 1: Envío de comando
            self._send_command(Command.STORAGE_STATUS)
            
            # Fase 2: Recepción de estado
            status_info = self._receive_json_response()
            
            # NO desconectar aquí - mantener conexión
            return status_info
            
        except Exception as e:
            logger.log("STATUS", f"Error obteniendo estado del almacenamiento: {str(e)}")
            self.disconnect()
            return None

    # =========================================================================
    # MÉTODO PARA CIERRE EXPLÍCITO
    # =========================================================================

    def close(self):
        """Cierra la conexión explícitamente (para cuando termine la aplicación)"""
        self.disconnect()
        logger.log("CLIENT", "Cliente cerrado explícitamente")

    # =========================================================================
    # MANEJO DE COMUNICACIÓN CON EL SERVIDOR (SIN CAMBIOS)
    # =========================================================================

    def _send_command(self, command: Command):
        """Envía un comando al servidor"""
        self.socket.send(command.to_bytes())

    def _send_filename(self, filename: str):
        """Envía un nombre de archivo al servidor"""
        filename_bytes = filename.encode('utf-8')
        self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        self.socket.send(filename_bytes)

    def _receive_response(self):
        """Recibe y parsea una respuesta del servidor"""
        response_bytes = self.socket.recv(4)
        return Response.from_bytes(response_bytes)

    def _receive_json_response(self):
        """Recibe y procesa una respuesta JSON del servidor"""
        # Recibir tamaño del JSON
        size_bytes = self.socket.recv(4)
        json_size = int.from_bytes(size_bytes, 'big')
        
        # Recibir datos JSON completos
        json_data = self._receive_complete_data(json_size)
        
        # Parsear y retornar
        return json.loads(json_data.decode('utf-8'))

    def _receive_complete_data(self, total_size: int):
        """Recibe una cantidad específica de datos del servidor"""
        data = b""
        while len(data) < total_size:
            chunk_size = min(self.BUFFER_SIZE, total_size - len(data))
            chunk = self.socket.recv(chunk_size)
            if not chunk:
                break
            data += chunk
        return data

    # =========================================================================
    # VALIDACIONES Y VERIFICACIONES (SIN CAMBIOS)
    # =========================================================================

    def _validate_local_file(self, file_path: str):
        """Valida que el archivo local exista"""
        if not os.path.exists(file_path):
            logger.log("CLIENT", f"Error: Archivo no encontrado - {file_path}")
            return False
        return True

    def _validate_download_availability(self, filename: str):
        """Valida que el archivo esté disponible para descarga"""
        response = self._receive_response()
        
        if response == Response.FILE_NOT_FOUND:
            logger.log("DOWNLOAD", f"Archivo no encontrado en servidor: {filename}")
            return False
        
        elif response != Response.SUCCESS:
            logger.log("DOWNLOAD", f"Error del servidor: {response}")
            return False
        
        return True

    # =========================================================================
    # MANEJO DE SUBIDA DE ARCHIVOS (SIN CAMBIOS)
    # =========================================================================

    def _send_file_metadata(self, filename: str, file_size: int):
        """Envía metadatos del archivo al servidor"""
        filename_bytes = filename.encode('utf-8')
        
        # Enviar nombre y tamaño
        self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        self.socket.send(filename_bytes)
        self.socket.send(file_size.to_bytes(8, 'big'))
        
        logger.log("UPLOAD", f"Metadata enviada: {filename} - {file_size} bytes")

    def _send_file_content(self, file_path: str, file_size: int):
        """Envía el contenido completo del archivo al servidor"""
        filename = os.path.basename(file_path)
        logger.log("UPLOAD", f"Enviando contenido del archivo...")
        
        with open(file_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(self.BUFFER_SIZE)
                self.socket.send(chunk)
                bytes_sent += len(chunk)
                
                # Mostrar progreso cada 1MB
                self._show_upload_progress(bytes_sent, file_size)

    def _show_upload_progress(self, bytes_sent: int, total_size: int):
        """Muestra el progreso de la subida"""
        if bytes_sent % (1024 * 1024) == 0 or bytes_sent == total_size:
            mb_sent = bytes_sent / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            logger.log("UPLOAD", f"Progreso envío: {mb_sent:.1f} / {mb_total:.1f} MB")

    def _handle_upload_response(self, filename: str):
        """Procesa la respuesta del servidor después de una subida"""
        response = self._receive_response()
        
        if response == Response.UPLOAD_COMPLETE:
            logger.log("UPLOAD", f"Subida completada: {filename}")
            return True
        elif response == Response.FILE_ALREADY_EXISTS:
            logger.log("UPLOAD", f"Error: El archivo ya existe en el servidor - {filename}")
            return False
        elif response == Response.STORAGE_FULL:
            logger.log("UPLOAD", f"Error: Capacidad de almacenamiento insuficiente para {filename}")
            return False
        else:
            logger.log("UPLOAD", f"Error en subida: {response}")
            return False

    # =========================================================================
    # MANEJO DE DESCARGA DE ARCHIVOS (SIN CAMBIOS)
    # =========================================================================

    def _receive_blocks_from_server(self):
        """Recibe todos los bloques del servidor"""
        # Fase 1: Recibir información de bloques
        blocks_info = self._receive_blocks_metadata()
        
        # Fase 2: Recibir contenido de bloques
        self._download_blocks_content(blocks_info)
        
        return blocks_info

    def _receive_blocks_metadata(self):
        """Recibe metadatos de los bloques del servidor"""
        logger.log("DOWNLOAD", "Recibiendo información de bloques...")
        
        # Recibir nombre del subdirectorio
        sub_dir = self._receive_string()
        
        # Recibir nombre del archivo
        filename = self._receive_string()
        
        # Recibir cantidad de bloques
        blocks_count = self._receive_integer(4)
        
        # Recibir nombres de bloques individuales
        blocks = self._receive_block_names(blocks_count)
            
        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks
        }

    def _receive_string(self):
        """Recibe una cadena de texto del servidor"""
        size_bytes = self.socket.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        string_bytes = self.socket.recv(size)
        return string_bytes.decode('utf-8')

    def _receive_integer(self, num_bytes: int):
        """Recibe un entero del servidor"""
        bytes_data = self.socket.recv(num_bytes)
        return int.from_bytes(bytes_data, 'big')

    def _receive_block_names(self, blocks_count: int):
        """Recibe los nombres de todos los bloques"""
        blocks = []
        for _ in range(blocks_count):
            block_name = self._receive_string()
            blocks.append(block_name)
        return blocks

    def _download_blocks_content(self, blocks_info: dict):
        """Descarga el contenido de todos los bloques"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        
        logger.log("DOWNLOAD", f"Recibiendo {len(blocks)} bloques: {filename}")
        
        # Crear directorio temporal para bloques
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        os.makedirs(sub_dir_path, exist_ok=True)
        
        # Descargar cada bloque individualmente
        for i, block in enumerate(blocks):
            self._download_single_block(block, sub_dir_path, i, len(blocks))

    def _download_single_block(self, block_name: str, sub_dir_path: str, block_index: int, total_blocks: int):
        """Descarga un bloque individual del servidor"""
        # Recibir tamaño del bloque
        block_size = self._receive_integer(8)
        
        # Descargar contenido del bloque
        block_path = os.path.join(sub_dir_path, block_name)
        self._download_block_content(block_path, block_size)
        
        logger.log("DOWNLOAD", f"Bloque {block_index+1}/{total_blocks} recibido: {block_name} - {block_size} bytes")

    def _download_block_content(self, block_path: str, block_size: int):
        """Descarga el contenido de un bloque específico"""
        with open(block_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < block_size:
                chunk_size = min(self.BUFFER_SIZE, block_size - bytes_received)
                chunk = self.socket.recv(chunk_size)
                f.write(chunk)
                bytes_received += len(chunk)

    def _process_downloaded_blocks(self, blocks_info: dict, save_path: str, filename: str):
        """Procesa los bloques descargados y reconstruye el archivo"""
        # Fase 1: Reconstrucción del archivo
        self._reconstruct_file_from_blocks(blocks_info, save_path)
        
        # Fase 2: Limpieza de temporales
        self._cleanup_temp_blocks(blocks_info)
        
        # Fase 3: Verificación final
        response = self._receive_response()
        
        if response == Response.DOWNLOAD_COMPLETE:
            logger.log("DOWNLOAD", f"Descarga completada: {filename} - {len(blocks_info['blocks'])} bloques")
            return True
        else:
            logger.log("DOWNLOAD", f"Error en descarga: {response}")
            return False

    # =========================================================================
    # RECONSTRUCCIÓN Y LIMPIEZA DE ARCHIVOS (SIN CAMBIOS)
    # =========================================================================

    def _reconstruct_file_from_blocks(self, blocks_info: dict, save_path: str):
        """Reconstruye el archivo a partir de los bloques descargados"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        # Crear directorio de destino
        file_path = os.path.join(save_path, filename)
        os.makedirs(save_path, exist_ok=True)
        
        logger.log("DOWNLOAD", f"Reconstruyendo archivo desde {len(blocks)} bloques...")
        
        # Unir bloques en archivo final
        union(blocks, file_path, sub_dir_path)
        
        logger.log("DOWNLOAD", f"Archivo reconstruido: {file_path}")

    def _cleanup_temp_blocks(self, blocks_info: dict):
        """Limpia los bloques temporales después de la reconstrucción"""
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        try:
            # Limpiar bloques individuales
            clean_blocks(blocks, sub_dir_path)
            
            # Limpiar directorios vacíos
            self._cleanup_empty_directories(sub_dir_path)
            
            logger.log("DOWNLOAD", f"Bloques temporales limpiados: {len(blocks)} bloques")
        
        except Exception as e:
            logger.log("DOWNLOAD", f"Error limpiando bloques temporales: {str(e)}")

    def _cleanup_empty_directories(self, sub_dir_path: str):
        """Elimina directorios temporales vacíos"""
        # Eliminar subdirectorio si está vacío
        if os.path.exists(sub_dir_path) and not os.listdir(sub_dir_path):
            os.rmdir(sub_dir_path)
        
        # Eliminar directorio temporal principal si está vacío
        if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
            os.rmdir(self.temp_dir)