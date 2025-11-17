# servidor/network_server.py
import socket
import threading
from core.event_manager import event_manager
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
        
        event_manager.publish(f"SERVER_STARTED: host: {self.host}, port: {self.port}")
        
        while True:
            client_socket, addr = self.socket.accept()
            
            print(f"CLIENT_CONNECTED: client_address: {addr[0]}, client_port: {addr[1]}")
            
            # Manejar cliente en hilo separado
            client_thread = threading.Thread(
                target=self.handle_client, 
                args=(client_socket, addr)
            )
            client_thread.start()
    
    def handle_client(self, client_socket:socket.socket, addr):
        try:
            client_socket.settimeout(30.0)

            while True:
                command_bytes = client_socket.recv(4)
                print(f"DEBUG: Bytes recibidos: {command_bytes.hex()} = {int.from_bytes(command_bytes, 'big')}")

                if not command_bytes:
                    break

                command = Command.from_bytes(command_bytes)
                print(f"Comando de {addr}: {command.name}")

                # Delegar al CommandHandler
                self.command_handler.handle_command(client_socket, command)
        except socket.timeout:
            print(f"Timeout con cliente {addr}")
        except Exception as e:
            print(f"CLIENT_HANDLER_ERROR: client_address={addr[0]}, client_port={addr[1]}, error={str(e)}")
        finally:
            client_socket.close()
            print(f"CLIENT_DISCONNECTED: client_address: {addr[0]}, client_port: {addr[1]}")