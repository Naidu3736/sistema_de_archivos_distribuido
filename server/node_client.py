# server/node_client.py (VERSIÓN CORREGIDA)
import socket
import json
from core.protocol import Command, Response
from core.network_utils import NetworkUtils
from core.logger import logger

class NodeClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def ping(self, host: str, port: int) -> bool:
        """Verifica si un nodo está activo"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((host, port))
                NetworkUtils.send_command(sock, Command.PING)
                response = NetworkUtils.receive_response(sock)
                return response == Response.SUCCESS
        except Exception as e:
            logger.log("NODE_CLIENT", f"Ping falló para {host}:{port}: {e}")
            return False

    def send_block(self, host: str, port: int, block_data: bytes, block_info: dict) -> bool:
        """Envía un bloque a un nodo de almacenamiento"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((host, port))
                
                # 1. Enviar comando UPLOAD_BLOCK
                NetworkUtils.send_command(sock, Command.UPLOAD_BLOCK)
                
                # 2. Enviar metadatos del bloque
                metadata = {
                    'filename': block_info['filename'],
                    'block_id': block_info['block_id'],
                    'physical_number': block_info['physical_number'],
                    'size': len(block_data),
                    'is_replica': block_info.get('is_replica', False)
                }
                NetworkUtils.send_json(sock, metadata)
                
                # 3. Esperar confirmación del nodo
                response = NetworkUtils.receive_response(sock)
                if response != Response.SUCCESS:
                    logger.log("NODE_CLIENT", f"Nodo rechazó bloque: {response}")
                    return False
                
                # 4. Enviar datos del bloque
                sock.sendall(block_data)
                
                # 5. Esperar confirmación final
                final_response = NetworkUtils.receive_response(sock)
                success = final_response == Response.UPLOAD_COMPLETE
                
                if success:
                    logger.log("NODE_CLIENT", f"Bloque {block_info['physical_number']} enviado exitosamente a {host}:{port}")
                else:
                    logger.log("NODE_CLIENT", f"Error enviando bloque a {host}:{port}: {final_response}")
                
                return success
                
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error enviando bloque a {host}:{port}: {e}")
            return False

    def get_block(self, host: str, port: int, block_info: dict) -> bytes:
        """Obtiene un bloque de un nodo de almacenamiento"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10.0)  # Timeout más generoso
                sock.connect((host, port))
                
                # Enviar comando DOWNLOAD_BLOCK
                NetworkUtils.send_command(sock, Command.DOWNLOAD_BLOCK)
                
                # Enviar metadatos del bloque
                metadata = {
                    'filename': block_info['filename'],
                    'block_id': block_info['block_id'],
                    'physical_number': block_info['physical_number']
                }
                NetworkUtils.send_json(sock, metadata)
                
                # Recibir respuesta del nodo
                response = NetworkUtils.receive_response(sock)
                if response != Response.SUCCESS:
                    logger.log("NODE_CLIENT", f"Nodo respondió con error: {response}")
                    return None
                
                # Recibir tamaño del bloque
                block_size = NetworkUtils.receive_file_size(sock)
                if block_size == 0:
                    return None
                
                # Recibir datos del bloque
                block_data = NetworkUtils.receive_exact_bytes(sock, block_size)
                
                logger.log("NODE_CLIENT", f"Bloque {block_info['physical_number']} recibido de {host}:{port} - {len(block_data)} bytes")
                return block_data
                
        except socket.timeout:
            logger.log("NODE_CLIENT", f"Timeout obteniendo bloque de {host}:{port}")
            return None
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error obteniendo bloque de {host}:{port}: {e}")
            return None

    def delete_block(self, host: str, port: int, block_info: dict) -> bool:
        """Elimina un bloque de un nodo de almacenamiento"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((host, port))
                
                # 1. Enviar comando DELETE_BLOCK
                NetworkUtils.send_command(sock, Command.DELETE_BLOCK)
                
                # 2. Enviar metadatos del bloque
                metadata = {
                    'filename': block_info['filename'],
                    'block_id': block_info['block_id'],
                    'physical_number': block_info['physical_number'],
                    'is_replica': block_info.get('is_replica', False)
                }
                NetworkUtils.send_json(sock, metadata)
                
                # 3. Esperar respuesta
                response = NetworkUtils.receive_response(sock)
                success = response == Response.SUCCESS
                
                if success:
                    logger.log("NODE_CLIENT", f"Bloque {block_info['physical_number']} eliminado de {host}:{port}")
                else:
                    logger.log("NODE_CLIENT", f"Error eliminando bloque de {host}:{port}: {response}")
                
                return success
                
        except Exception as e:
            logger.log("NODE_CLIENT", f"Error eliminando bloque de {host}:{port}: {e}")
            return False