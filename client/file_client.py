import socket
import os
import json
from core.protocol import Command, Response
from core.logger import logger

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
        
        logger.log("CLIENT", f"Cliente de archivos configurado - Servidor: {host_server}:{port_server}")
    
    # =========================================================================
    # GESTIÓN DE CONEXIÓN Y DESCONEXIÓN
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
        return True

    # =========================================================================
    # OPERACIONES PRINCIPALES CON ARCHIVOS (STREAMING)
    # =========================================================================

    def upload_file(self, file_path: str):
        """Sube un archivo al sistema distribuido de archivos en streaming"""
        if not self.ensure_connection():
            return False
        
        if not self._validate_local_file(file_path):
            return False
            
        try:
            logger.log("UPLOAD", "Iniciando subida de archivo en streaming...")
            
            # Fase 1: Envío de comando y metadatos
            self._send_command(Command.UPLOAD)
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.log("UPLOAD", f"Subiendo archivo: {filename} ({file_size} bytes)")
            self._send_file_metadata(filename, file_size)

            # Fase 2: Esperar confirmación del servidor para proceder
            response = self._receive_response()
            if response != Response.SUCCESS:
                self._handle_upload_error(response, filename)
                return False
            
            # Fase 3: Envío del contenido en streaming
            self._stream_file_content(file_path, file_size)
    
            # Fase 4: Verificación de respuesta
            response = self._receive_response()
            if response == Response.UPLOAD_COMPLETE:
                logger.log("UPLOAD", f"Carga de archivo completada: {filename}")
                return True
            else:
                logger.log("UPLOAD", f"Error al cargar archivo: {response}")
                return False
            
        except Exception as e:
            logger.log("UPLOAD", f"Error durante subida: {str(e)}")
            self.disconnect()
            return False

    def download_file(self, filename: str, save_path: str):
        """Descarga un archivo del sistema distribuido de archivos en streaming"""
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
            
            # Fase 3: Recepción y reconstrucción en streaming
            success = self._receive_and_save_streaming_file(save_path, filename)
            
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
                return True
            elif response == Response.FILE_NOT_FOUND:
                logger.log("DELETE", f"Archivo no encontrado: {filename}")
                return False
            else:
                logger.log("DELETE", f"Error en eliminación: {response}")
                return False
            
        except Exception as e:
            logger.log("DELETE", f"Error durante eliminación: {str(e)}")
            self.disconnect()
            return False

    # =========================================================================
    # OPERACIONES DE CONSULTA E INFORMACIÓN
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
            
            return status_info
            
        except Exception as e:
            logger.log("STATUS", f"Error obteniendo estado del almacenamiento: {str(e)}")
            self.disconnect()
            return None

    # =========================================================================
    # MÉTODO PARA CIERRE EXPLÍCITO
    # =========================================================================

    def close(self):
        """Cierra la conexión explícitamente"""
        self.disconnect()
        logger.log("CLIENT", "Cliente cerrado explícitamente")

    # =========================================================================
    # MANEJO DE COMUNICACIÓN CON EL SERVIDOR
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
    # STREAMING DE SUBIDA DE ARCHIVOS
    # =========================================================================

    def _send_file_metadata(self, filename: str, file_size: int):
        """Envía metadatos del archivo al servidor"""
        filename_bytes = filename.encode('utf-8')
        
        # Enviar nombre y tamaño
        self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        self.socket.send(filename_bytes)
        self.socket.send(file_size.to_bytes(8, 'big'))
        
        logger.log("UPLOAD", f"Metadata enviada: {filename} - {file_size} bytes")

    def _stream_file_content(self, file_path: str, file_size: int):
        """Envía el contenido completo del archivo al servidor en streaming"""
        filename = os.path.basename(file_path)
        logger.log("UPLOAD", f"Transmitiendo contenido del archivo en streaming...")
        
        with open(file_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                self.socket.send(chunk)
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

    # =========================================================================
    # STREAMING DE DESCARGA DE ARCHIVOS
    # =========================================================================

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
        response = self._receive_response()
        
        if response == Response.DOWNLOAD_COMPLETE:
            logger.log("DOWNLOAD", f"Descarga completada: {filename} - {total_bytes_received} bytes recibidos")
            return True
        else:
            logger.log("DOWNLOAD", f"Error en descarga: {response}")
            return False

    def _receive_streaming_metadata(self):
        """Recibe metadatos del streaming del servidor"""
        # Recibir nombre del archivo
        filename_size = int.from_bytes(self.socket.recv(4), 'big')
        filename_bytes = self.socket.recv(filename_size)
        filename = filename_bytes.decode('utf-8')
        
        # Recibir cantidad de bloques
        block_count = int.from_bytes(self.socket.recv(4), 'big')
        
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
        block_size = int.from_bytes(self.socket.recv(8), 'big')
        
        if block_size == 0:
            logger.log("ERROR", f"Bloque {block_index+1} faltante en el servidor")
            return 0
        
        # Recibir y escribir contenido del bloque
        bytes_received = 0
        while bytes_received < block_size:
            chunk_size = min(self.BUFFER_SIZE, block_size - bytes_received)
            chunk = self.socket.recv(chunk_size)
            if not chunk:
                break
            output_file.write(chunk)
            bytes_received += len(chunk)
        
        logger.log("DOWNLOAD", f"Bloque {block_index+1}/{total_blocks} recibido: {bytes_received} bytes")
        return bytes_received

    # =========================================================================
    # VALIDACIONES
    # =========================================================================

    def _validate_local_file(self, file_path: str):
        """Valida que el archivo local exista"""
        if not os.path.exists(file_path):
            logger.log("CLIENT", f"Error: Archivo no encontrado - {file_path}")
            return False
        return True