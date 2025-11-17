# servidor/network_server.py
import socket
import threading
from server.file_server import FileServer
from server.command_handler import CommandHandler
from core.protocol import Command

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.socket = None
        self.file_server = FileServer()
        self.command_handler = CommandHandler(self.file_server)
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        print(f"SERVER_STARTED: host={self.host}, port={self.port}")
        print(f"Servidor escuchando en {self.host}:{self.port}")
        
        while True:
            client_socket, addr = self.socket.accept()
            self._handle_new_client(client_socket, addr)
    
    def _handle_new_client(self, client_socket: socket.socket, addr):
        """Maneja una nueva conexión de cliente"""
        print(f"CLIENT_CONNECTED: client_address={addr[0]}, client_port={addr[1]}")
        print(f"Nuevo cliente conectado: {addr[0]}:{addr[1]}")
        
        # Manejar cliente en hilo separado
        client_thread = threading.Thread(
            target=self._client_session, 
            args=(client_socket, addr),
            daemon=True
        )
        client_thread.start()

    def _client_session(self, client_socket: socket.socket, addr):
        """Maneja la sesión de un cliente específico"""
        try:
            client_socket.settimeout(10.0)
            self._process_client_commands(client_socket, addr)
            
        except socket.timeout:
            print(f"Timeout con cliente {addr} - Cerrando conexión")
        except Exception as e:
            print(f"Error en sesión con cliente {addr}: {str(e)}")
        finally:
            client_socket.close()
            print(f"CLIENT_DISCONNECTED: client_address={addr[0]}, client_port={addr[1]}")
            print(f"Cliente {addr} desconectado")

    def _process_client_commands(self, client_socket: socket.socket, addr):
        """Procesa los comandos de un cliente en loop"""
        while True:
            command_bytes = client_socket.recv(4)
            
            # Cliente cerró la conexión
            if not command_bytes:
                print(f"Cliente {addr} cerró la conexión")
                break

            # Procesar comando
            if not self._execute_command(client_socket, addr, command_bytes):
                break

    def _execute_command(self, client_socket: socket.socket, addr, command_bytes):
        """Ejecuta un comando específico"""
        try:
            command = Command.from_bytes(command_bytes)
            print(f"Comando de {addr}: {command.name}")

            self.command_handler.handle_command(client_socket, command)
            return True
            
        except ValueError as e:
            print(f"Comando inválido de {addr}: {e}")
            return False
        except Exception as e:
            print(f"Error ejecutando comando de {addr}: {e}")
            return False

    def stop(self):
        """Detiene el servidor"""
        if self.socket:
            self.socket.close()
            print("Servidor detenido")