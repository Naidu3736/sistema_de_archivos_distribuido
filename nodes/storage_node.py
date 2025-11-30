# nodes/storage_node.py (VERSIÓN CORREGIDA)
import socket
import threading
import os
import time
from typing import Dict, Optional
from core.protocol import Command, Response
from core.network_utils import NetworkUtils
from core.logger import logger

class StorageNode:
    """Nodo de almacenamiento que guarda bloques en estructura organizada"""
    
    def __init__(self, host='0.0.0.0', port=8002, storage_base_dir: str = "blocks", buffer_size: int = 64 * 1024):
        self.host = host
        self.port = port
        self.storage_base_dir = storage_base_dir
        self.BUFFER_SIZE = buffer_size
        self.used_space_mb = 0
        
        # Crear directorio base
        os.makedirs(storage_base_dir, exist_ok=True)
        
        self.socket = None
        self.running = False
        self.lock = threading.RLock()
        
        logger.log("STORAGE_NODE", f"Nodo iniciado en {host}:{port} - Directorio: {storage_base_dir}")

    def _get_block_directory(self, filename: str) -> str:
        """Obtiene el directorio específico para los bloques de un archivo"""
        # Usar hash del filename para evitar problemas con caracteres especiales
        filename = os.path.basename(filename)
        file_splitext = os.path.splitext(filename)[0]
        block_dir = os.path.join(self.storage_base_dir, file_splitext)
        return block_dir

    def _get_block_path(self, filename: str, physical_number: int) -> str:
        """Obtiene la ruta completa para un bloque específico"""
        block_dir = self._get_block_directory(filename)
        block_filename = f"block_{physical_number}.bin"
        return os.path.join(block_dir, block_filename)

    def start(self):
        """Inicia el servidor del nodo de almacenamiento"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.socket.settimeout(1.0)

        self.running = True
        
        logger.log("STORAGE_NODE", f"Escuchando en {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                self._handle_node_client(client_socket, addr)
            
            except socket.timeout:
                continue
            except OSError as e:
                if self.running:
                    logger.log("STORAGE_NODE", f"Error aceptando conexión: {e}")
                break
            except Exception as e:
                logger.log("STORAGE_NODE", f"Error inesperado: {e}")
                break

    def _handle_node_client(self, client_socket: socket.socket, addr):
        """Maneja conexiones del coordinador"""
        logger.log("STORAGE_NODE", f"Conexión del coordinador: {addr[0]}:{addr[1]}")
        
        client_thread = threading.Thread(
            target=self._node_client_session, 
            args=(client_socket, addr),
            daemon=True
        )
        client_thread.start()

    def _node_client_session(self, client_socket: socket.socket, addr):
        """Sesión con el coordinador"""
        try:
            client_socket.settimeout(30.0)
            
            while self.running:
                try:
                    command_bytes = client_socket.recv(4)
                    if not command_bytes:
                        break
                    
                    self._execute_node_command(client_socket, addr, command_bytes)
                        
                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
                except Exception as e:
                    logger.log("STORAGE_NODE", f"Error con coordinador {addr}: {e}")
                    break
                    
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error en sesión con coordinador {addr}: {e}")
        finally:
            client_socket.close()

    def _execute_node_command(self, client_socket: socket.socket, addr, command_bytes):
        """Ejecuta comandos específicos de nodos"""
        try:
            command = Command.from_bytes(command_bytes)
            logger.log("STORAGE_NODE", f"Comando recibido: {command.name} de {addr}")

            if command == Command.UPLOAD_BLOCK:
                self._handle_upload_block(client_socket)
            elif command == Command.DOWNLOAD_BLOCK:
                self._handle_download_block(client_socket)
            elif command == Command.DELETE_BLOCKS:
                self._handle_delete_blocks(client_socket)
            elif command == Command.PING:
                self._handle_ping(client_socket)
            else:
                logger.log("STORAGE_NODE", f"Comando no reconocido: {command}")
                NetworkUtils.send_response(client_socket, Response.SERVER_ERROR)
                
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error ejecutando comando: {e}")
            NetworkUtils.send_response(client_socket, Response.SERVER_ERROR)

    def _handle_upload_block(self, client_socket: socket.socket):
        """Procesa subida SIN verificar espacio - el coordinador ya lo hizo"""
        try:
            # 1. Recibir metadata del bloque
            metadata = NetworkUtils.receive_json(client_socket)
            
            # 2. Confirmar recepción inmediatamente
            NetworkUtils.send_response(client_socket, Response.SUCCESS)
            
            # 3. Crear directorio y guardar bloque
            filename = metadata['filename']
            physical_number = metadata['physical_number']
            block_size = metadata['size']
            
            block_dir = self._get_block_directory(filename)
            os.makedirs(block_dir, exist_ok=True)
            block_path = self._get_block_path(filename, physical_number)
            
            # 4. Recibir y guardar el bloque
            self._save_block_from_stream(client_socket, block_path, block_size)
            
            # 5. Actualizar espacio usado (solo para monitoreo, no para decisiones)
            with self.lock:
                self.used_space_mb += block_size / (1024 * 1024)
            
            # 6. Confirmar completado
            NetworkUtils.send_response(client_socket, Response.UPLOAD_COMPLETE)
            logger.log("STORAGE_NODE", f"Bloque guardado: {block_path}")
            
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error subiendo bloque: {e}")
            NetworkUtils.send_response(client_socket, Response.SERVER_ERROR)

    def _handle_download_block(self, client_socket: socket.socket):
        """Procesa la descarga de un bloque"""
        try:
            # 1. Recibir metadata del bloque
            metadata = NetworkUtils.receive_json(client_socket)
            logger.log("STORAGE_NODE", f"Metadata descarga: {metadata}")
            
            filename = metadata['filename']
            block_id = metadata['block_id']
            physical_number = metadata['physical_number']
            
            # 2. Verificar que el bloque existe
            block_path = self._get_block_path(filename, physical_number)
            if not os.path.exists(block_path):
                NetworkUtils.send_response(client_socket, Response.FILE_NOT_FOUND)
                logger.log("STORAGE_NODE", f"Bloque no encontrado: {block_path}")
                return
            
            NetworkUtils.send_response(client_socket, Response.SUCCESS)

            # 3. Enviar tamaño del bloque
            block_size = os.path.getsize(block_path)
            NetworkUtils.send_file_size(client_socket, block_size)
            
            # 4. Enviar datos del bloque
            self._send_block_to_client(client_socket, block_path)
            
            logger.log("STORAGE_NODE", f"Bloque enviado: {block_path} ({block_size} bytes)")
            
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error descargando bloque: {e}")
            NetworkUtils.send_response(client_socket, Response.SERVER_ERROR)

    def _handle_delete_blocks(self, client_socket: socket.socket):
        """Elimina todos los bloques de un archivo específico"""
        try:
            # 1. Recibir nombre del archivo
            filename = NetworkUtils.receive_filename(client_socket)
            
            logger.log("STORAGE_NODE", f"Eliminando todos los bloques del archivo: {filename}")
            
            # 2. Obtener directorio del archivo
            block_dir = self._get_block_directory(filename)
            
            if not os.path.exists(block_dir):
                logger.log("STORAGE_NODE", f"Directorio no encontrado: {block_dir}")
                NetworkUtils.send_response(client_socket, Response.SUCCESS)
                return
            
            # 3. Eliminar todos los bloques del directorio
            deleted_count = 0
            total_size_freed = 0
            
            for block_file in os.listdir(block_dir):
                if block_file.endswith('.bin'):
                    block_path = os.path.join(block_dir, block_file)
                    try:
                        block_size = os.path.getsize(block_path)
                        os.remove(block_path)
                        deleted_count += 1
                        total_size_freed += block_size
                        logger.log("STORAGE_NODE", f"Bloque eliminado: {block_path}")
                    except Exception as e:
                        logger.log("STORAGE_NODE", f"Error eliminando {block_path}: {e}")
            
            # 4. Actualizar espacio usado
            with self.lock:
                self.used_space_mb = max(0, self.used_space_mb - (total_size_freed / (1024 * 1024)))
            
            # 5. Intentar eliminar directorio si está vacío
            try:
                if not os.listdir(block_dir):
                    os.rmdir(block_dir)
                    logger.log("STORAGE_NODE", f"Directorio eliminado: {block_dir}")
            except OSError:
                pass  # El directorio no está vacío
            
            # 6. Responder éxito
            NetworkUtils.send_response(client_socket, Response.SUCCESS)
            logger.log("STORAGE_NODE", f"Eliminación completada: {deleted_count} bloques de '{filename}'")
            
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error eliminando bloques: {e}")
            NetworkUtils.send_response(client_socket, Response.SERVER_ERROR)

    def _handle_ping(self, client_socket: socket.socket):
        """Responde a ping del coordinador"""
        NetworkUtils.send_response(client_socket, Response.SUCCESS)
        logger.log("STORAGE_NODE", "Ping respondido")

    def _save_block_from_stream(self, client_socket: socket.socket, block_path: str, block_size: int):
        """Guarda un bloque desde el stream"""
        with open(block_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < block_size:
                chunk_size = min(self.BUFFER_SIZE, block_size - bytes_received)
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)

    def _send_block_to_client(self, client_socket: socket.socket, block_path: str):
        """Envía un bloque al cliente"""
        with open(block_path, 'rb') as f:
            while True:
                chunk = f.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                client_socket.send(chunk)

    def stop(self):
        """Detiene el nodo de almacenamiento"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.log("STORAGE_NODE", "Nodo de almacenamiento detenido")


    def cleanup_empty_directories(self):
        """Limpia directorios vacíos"""
        if not os.path.exists(self.storage_base_dir):
            return
        
        directories_removed = 0
        for basename in os.listdir(self.storage_base_dir):
            block_dir = os.path.join(self.storage_base_dir, basename)
            if os.path.isdir(block_dir) and not os.listdir(block_dir):
                try:
                    os.rmdir(block_dir)
                    directories_removed += 1
                    logger.log("STORAGE_NODE", f"Directorio vacío eliminado: {block_dir}")
                except OSError as e:
                    logger.log("STORAGE_NODE", f"Error eliminando directorio {block_dir}: {e}")
        
        if directories_removed > 0:
            logger.log("STORAGE_NODE", f"Limpieza completada: {directories_removed} directorios vacíos eliminados")