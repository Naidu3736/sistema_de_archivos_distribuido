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
        
        event_manager.publish('SERVER_STARTED', {
            'host': self.host,
            'port': self.port
        })
        
        while True:
            client_socket, addr = self.socket.accept()
            
            event_manager.publish('CLIENT_CONNECTED', {
                'client_address': addr[0],
                'client_port': addr[1]
            })
            
            # Manejar cliente en hilo separado
            client_thread = threading.Thread(
                target=self.handle_client, 
                args=(client_socket, addr)
            )
            client_thread.start()
    
    def handle_client(self, client_socket:socket.socket, addr):
        try:
            # Recibir comando
            command_bytes = client_socket.recv(4)
            command = Command.from_bytes(command_bytes)

            # Delegar al CommandHandler
            self.command_handler.handle_command(client_socket, command)
                    
        except Exception as e:
            event_manager.publish('CLIENT_HANDLER_ERROR', {
                'client_address': addr[0],
                'client_port': addr[1],
                'error': str(e)
            })
        finally:
            client_socket.close()