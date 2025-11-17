# servidor/network_server.py
import socket
import threading
from core.event_manager import event_manager
from server.file_server import FileServer

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.socket = None
        self.file_server = FileServer()
    
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
    
    def handle_client(self, client_socket, addr):
        try:
            # Recibir operación del cliente
            operation_bytes = client_socket.recv(1024)
            if not operation_bytes:
                return
                
            operation = operation_bytes.decode('utf-8').strip()
            
            event_manager.publish('CLIENT_OPERATION', {
                'client_address': addr[0],
                'client_port': addr[1],
                'operation': operation
            })
            
            if operation == "DOWNLOAD":
                # Recibir nombre del archivo
                filename_size = int.from_bytes(client_socket.recv(4), 'big')
                filename_bytes = client_socket.recv(filename_size)
                filename = filename_bytes.decode('utf-8')
                
                self.file_server.process_download_request(client_socket)
                
            elif operation == "UPLOAD":
                self.file_server.process_upload_request(client_socket)
                
            elif operation == "LIST_FILES":
                # Por implementar
                event_manager.publish('LIST_FILES_REQUEST', {
                    'client_address': addr[0],
                    'client_port': addr[1]
                })
                client_socket.send(b"OPERATION_NOT_IMPLEMENTED")
                
            else:
                event_manager.publish('UNKNOWN_OPERATION', {
                    'client_address': addr[0], 
                    'client_port': addr[1],
                    'operation': operation
                })
                client_socket.send(b"UNKNOWN_OPERATION")
                
        except Exception as e:
            event_manager.publish('CLIENT_HANDLER_ERROR', {
                'client_address': addr[0],
                'client_port': addr[1],
                'error': str(e)
            })
        finally:
            client_socket.close()
            event_manager.publish('CLIENT_DISCONNECTED', {
                'client_address': addr[0],
                'client_port': addr[1]
            })
    
    def stop(self):
        if self.socket:
            self.socket.close()
            event_manager.publish('SERVER_STOPPED', {})