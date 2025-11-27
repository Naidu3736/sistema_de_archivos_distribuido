# network_server.py (CORREGIDO)
import socket
import threading
from server.file_server import FileServer
from core.protocol import Command
from core.logger import logger

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=8001, number_clients: int = 20):
        self.host = host
        self.port = port
        self.number_clients = number_clients
        self.file_server = FileServer()
        self.socket = None
        self.running = False

    def start(self):
        """Inicia el servidor"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.number_clients)
            self.socket.settimeout(1.0)  # Timeout para poder verificar self.running
            self.running = True
            
            logger.log("SERVER", f"Servidor iniciado en {self.host}:{self.port}")
            logger.log("SERVER", f"Capacidad: {self.file_server.capacity_mb}MB")
            logger.log("SERVER", f"Máximo de clientes: {self.number_clients}")
            
            self._accept_connections()
            
        except Exception as e:
            logger.log("SERVER", f"Error iniciando servidor: {e}")
            self.stop()

    def _accept_connections(self):
        """Acepta conexiones de clientes"""
        logger.log("SERVER", "Esperando conexiones...")
        
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                self._handle_new_client(client_socket, addr)
            
            except socket.timeout:
                # Timeout normal, verificar si debemos continuar
                continue
            except OSError as e:
                # Error cuando el socket se cierra durante accept()
                if self.running:
                    logger.log("SERVER", f"Error aceptando conexión: {e}")
                break
            except Exception as e:
                logger.log("SERVER", f"Error inesperado: {e}")
                break

    def _handle_new_client(self, client_socket: socket.socket, addr):
        """Maneja una nueva conexión de cliente"""
        logger.log("NETWORK", f"CLIENT_CONNECTED: client_address={addr[0]}, client_port={addr[1]}")
        
        # Manejar cliente en hilo separado
        client_thread = threading.Thread(
            target=self._client_session, 
            args=(client_socket, addr),
            daemon=True
        )
        client_thread.start()

    def _client_session(self, client_socket: socket.socket, addr):
        """Maneja la sesión de un cliente específico"""
        logger.log("NETWORK", f"Sesión iniciada con cliente {addr}")
        
        try:
            # Configurar timeout para no bloquear indefinidamente
            client_socket.settimeout(30.0)  # 30 segundos de timeout
            
            while self.running:
                try:
                    # Esperar comandos del cliente
                    command_bytes = client_socket.recv(4)
                    
                    # Si no hay datos, conexión cerrada
                    if not command_bytes:
                        logger.log("NETWORK", f"Conexión cerrada por cliente {addr}")
                        break
                    
                    # Procesar el comando
                    self._execute_command(client_socket, addr, command_bytes)
                        
                except socket.timeout:
                    # Timeout normal, continuar esperando más comandos
                    continue
                except ConnectionResetError:
                    logger.log("NETWORK", f"Cliente {addr} cerró la conexión abruptamente")
                    break
                except BrokenPipeError:
                    logger.log("NETWORK", f"Conexión rota con cliente {addr}")
                    break
                except Exception as e:
                    logger.log("NETWORK", f"Error recibiendo comando de {addr}: {str(e)}")
                    break
                    
        except Exception as e:
            logger.log("NETWORK", f"Error en sesión con cliente {addr}: {str(e)}")
        finally:
            # Cerrar conexión
            try:
                client_socket.close()
                logger.log("NETWORK", f"Conexión cerrada con cliente {addr}")
            except:
                pass

    def _execute_command(self, client_socket: socket.socket, addr, command_bytes):
        """Ejecuta un comando específico"""
        try:
            command = Command.from_bytes(command_bytes)
            logger.log("COMMAND", f"Comando de {addr}: {command.name}")

            # Delegar al file_server según el comando
            if command == Command.UPLOAD:
                self.file_server.process_upload_request(client_socket)
            elif command == Command.DOWNLOAD:
                self.file_server.process_download_request(client_socket)
            elif command == Command.DELETE:
                self.file_server.process_delete_request(client_socket)
            elif command == Command.LIST:
                self.file_server.process_list_request(client_socket)
            elif command == Command.INFO:
                self.file_server.process_info_request(client_socket)
            elif command == Command.STORAGE_STATUS:
                self.file_server.process_storage_status_request(client_socket)
            elif command == Command.BLOCK_TABLE:
                self.file_server.process_block_table_request(client_socket)
            else:
                logger.log("COMMAND", f"Comando no reconocido: {command}")
            
        except ValueError as e:
            logger.log("COMMAND", f"Comando inválido de {addr}: {e}")
        except Exception as e:
            logger.log("COMMAND", f"Error ejecutando comando de {addr}: {e}")

    def stop(self):
        """Detiene el servidor"""
        logger.log("SERVER", "Deteniendo servidor...")
        self.running = False
        if self.socket:
            self.socket.close()
        self.file_server.cleanup()
        logger.log("SERVER", "Servidor detenido")