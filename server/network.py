# servidor/network_server.py
import socket
import threading

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.socket = None
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"Servidor escuchando en {self.host}:{self.port}")
        
        while True:
            client_socket, addr = self.socket.accept()
            print(f"Cliente conectado: {addr}")
            
            # Manejar cliente en hilo separado
            client_thread = threading.Thread(
                target=self.handle_client, 
                args=(client_socket, addr)
            )
            client_thread.start()
    
    def handle_client(self, client_socket, addr):
        try:
            # Recibir operación del cliente
            operation = client_socket.recv(1024).decode('utf-8').strip()
            
            if operation == "DOWNLOAD":
                filename = client_socket.recv(1024).decode('utf-8').strip()
                self.file_server.handle_download(client_socket, filename)
                
            elif operation == "UPLOAD":
                filename = client_socket.recv(1024).decode('utf-8').strip()
                self.file_server.handle_upload(client_socket, filename)
                
            elif operation == "LIST":
                self.file_server.handle_list(client_socket)
                
        except Exception as e:
            print(f"Error con cliente {addr}: {e}")
        finally:
            client_socket.close()