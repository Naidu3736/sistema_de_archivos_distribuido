import socket
import threading
from typing import Optional
from core.protocol import Command, Response
from core.network_utils import NetworkUtils
from core.logger import logger

class NodeClient:
    """Cliente para comunicarse con nodos de almacenamiento - CONEXIONES EFÍMERAS"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def _create_connection(self, host: str, port: int) -> Optional[socket.socket]:
        """Crea una conexión temporal al nodo"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            return sock
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error conectando a {host}:{port}: {e}")
            return None

    def send_block(self, host: str, port: int, block_data: bytes, block_info: dict) -> bool:
        """Envía un bloque a un nodo usando conexión temporal"""
        sock = self._create_connection(host, port)
        if not sock:
            return False
        
        try:
            # 1. Enviar comando UPLOAD_BLOCK
            NetworkUtils.send_command(sock, Command.UPLOAD_BLOCK)
            
            # 2. Enviar metadata del bloque
            metadata = {
                'block_id': block_info['block_id'],
                'filename': block_info['filename'],
                'size': len(block_data)
            }
            NetworkUtils.send_json(sock, metadata)
            
            # 3. Esperar confirmación
            response = NetworkUtils.receive_response(sock)
            if response != Response.SUCCESS:
                return False
            
            # 4. Enviar datos del bloque (usando send_exact_bytes)
            NetworkUtils.send_exact_bytes(sock, block_data)
            
            # 5. Esperar confirmación final
            response = NetworkUtils.receive_response(sock)
            return response == Response.UPLOAD_COMPLETE
            
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error enviando bloque a {host}:{port}: {e}")
            return False
        finally:
            # SIEMPRE cerrar la conexión
            try:
                sock.close()
            except:
                pass

    def get_block(self, host: str, port: int, block_info: dict) -> Optional[bytes]:
        """Obtiene un bloque de un nodo usando conexión temporal"""
        sock = self._create_connection(host, port)
        if not sock:
            return None
        
        try:
            # 1. Enviar comando DOWNLOAD_BLOCK
            NetworkUtils.send_command(sock, Command.DOWNLOAD_BLOCK)
            
            # 2. Enviar metadata del bloque
            metadata = {
                'block_id': block_info['block_id'],
                'filename': block_info['filename']
            }
            NetworkUtils.send_json(sock, metadata)
            
            # 3. Recibir tamaño del bloque
            block_size = NetworkUtils.receive_file_size(sock)
            if block_size == 0:
                return None
            
            # 4. Recibir datos del bloque (usando receive_exact_bytes)
            block_data = NetworkUtils.receive_exact_bytes(sock, block_size)
            return block_data
            
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error obteniendo bloque de {host}:{port}: {e}")
            return None
        finally:
            try:
                sock.close()
            except:
                pass

    def delete_block(self, host: str, port: int, block_info: dict) -> bool:
        """Elimina un bloque de un nodo usando conexión temporal"""
        sock = self._create_connection(host, port)
        if not sock:
            return False
        
        try:
            # 1. Enviar comando DELETE_BLOCK
            NetworkUtils.send_command(sock, Command.DELETE_BLOCK)
            
            # 2. Enviar metadata del bloque
            metadata = {
                'block_id': block_info['block_id'],
                'filename': block_info['filename']
            }
            NetworkUtils.send_json(sock, metadata)
            
            # 3. Esperar confirmación
            response = NetworkUtils.receive_response(sock)
            return response == Response.SUCCESS
            
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error eliminando bloque de {host}:{port}: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass

    def ping(self, host: str, port: int) -> bool:
        """Verifica si el nodo está activo usando conexión temporal"""
        sock = self._create_connection(host, port)
        if not sock:
            return False
        
        try:
            NetworkUtils.send_command(sock, Command.PING)
            response = NetworkUtils.receive_response(sock)
            return response == Response.SUCCESS
        except Exception as e:
            return False
        finally:
            try:
                sock.close()
            except:
                pass

    def get_node_status(self, host: str, port: int) -> Optional[dict]:
        """Obtiene el estado de un nodo"""
        sock = self._create_connection(host, port)
        if not sock:
            return None
        
        try:
            NetworkUtils.send_command(sock, Command.STORAGE_STATUS)
            response = NetworkUtils.receive_response(sock)
            if response != Response.SUCCESS:
                return None
            
            # Recibir datos de estado en JSON
            status_data = NetworkUtils.receive_json(sock)
            return status_data
            
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error obteniendo estado de {host}:{port}: {e}")
            return None
        finally:
            try:
                sock.close()
            except:
                pass

    def receive_file_from_node(self, host: str, port: int, block_info: dict, output_path: str) -> bool:
        """Recibe un archivo completo de un nodo (para archivos grandes)"""
        sock = self._create_connection(host, port)
        if not sock:
            return False
        
        try:
            # 1. Enviar comando DOWNLOAD_BLOCK
            NetworkUtils.send_command(sock, Command.DOWNLOAD_BLOCK)
            
            # 2. Enviar metadata del bloque
            metadata = {
                'block_id': block_info['block_id'],
                'filename': block_info['filename']
            }
            NetworkUtils.send_json(sock, metadata)
            
            # 3. Recibir archivo en chunks
            NetworkUtils.receive_file_chunked(sock, output_path)
            
            # Verificar que el archivo se recibió correctamente
            import os
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error recibiendo archivo de {host}:{port}: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass