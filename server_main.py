import time
from server.network_server import NetworkServer

def main():
    print("Iniciando Servidor DFS...")
    
    # Crear y iniciar servidor
    server = NetworkServer(host='192.168.101.9', port=8001)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("Deteniendo servidor...")
        server.stop()

if __name__ == "__main__":
    main()