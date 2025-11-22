import socket
import threading
from server.file_server import FileServer
from server.command_handler import CommandHandler
from core.protocol import Command
from core.logger import logger

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.file_server = FileServer()
        self.command_handler = CommandHandler(self.file_server)
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.socket.settimeout(1.0)

        self.running = True
        
        logger.log("SERVER", f"SERVER_STARTED: host={self.host}, port={self.port}")
        logger.log("SERVER", f"Servidor escuchando en {self.host}:{self.port}")
        
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
        logger.log("NETWORK", f"Nuevo cliente conectado: {addr[0]}:{addr[1]}")
        
        # Manejar cliente en hilo separado
        client_thread = threading.Thread(
            target=self._client_session, 
            args=(client_socket, addr),
            daemon=True
        )
        client_thread.start()

    def _client_session(self, client_socket: socket.socket, addr):
        """Maneja la sesión de un cliente específico - CONEXIÓN PERSISTENTE"""
        logger.log("NETWORK", f"Sesión persistente iniciada con cliente {addr}")
        
        try:
            # Configurar timeout para no bloquear indefinidamente
            client_socket.settimeout(0.5)
            
            while self.running:
                try:
                    # Esperar comandos del cliente
                    command_bytes = client_socket.recv(4)
                    
                    # Si no hay datos (timeout), continuar esperando
                    if not command_bytes:
                        logger.log("NETWORK", f"Conexión perdida con cliente {addr} \ {command_bytes}")
                        break
                    
                    # Procesar el comando
                    self._execute_command(client_socket, addr, command_bytes)
                        
                except socket.timeout:
                    # Timeout normal, continuar esperando más comandos
                    continue
                except ConnectionResetError:
                    logger.log("NETWORK", f"Cliente {addr} cerró la conexión")
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
            # Solo cerrar cuando realmente termine la sesión
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

            self.command_handler.handle_command(client_socket, command)
            
        except ValueError as e:
            logger.log("COMMAND", f"Comando inválido de {addr}: {e}")
        except Exception as e:
            logger.log("COMMAND", f"Error ejecutando comando de {addr}: {e}")

    def stop(self):
        """Detiene el servidor"""
        self.running = False
        if self.socket:
            self.socket.close()
            logger.log("SERVER", "Servidor detenido")