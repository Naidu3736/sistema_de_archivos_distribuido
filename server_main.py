# server_main.py
import time
from core.event_manager import event_manager
from server.network_server import NetworkServer

# Consumidor simple para servidor
def server_logger(event):
    event_type = event['type']
    timestamp = event['timestamp']
    
    if event_type == 'SERVER_STARTED':
        data = event['data']
        print(f"🚀 [{timestamp}] Servidor iniciado en {data['host']}:{data['port']}")
    
    elif event_type == 'CLIENT_CONNECTED':
        data = event['data']
        print(f"🔗 [{timestamp}] Cliente conectado: {data['client_address']}:{data['client_port']}")
    
    elif event_type == 'CLIENT_OPERATION':
        data = event['data']
        print(f"📨 [{timestamp}] Operación desde {data['client_address']}: {data['operation']}")
    
    elif event_type == 'CLIENT_DISCONNECTED':
        data = event['data']
        print(f"🔌 [{timestamp}] Cliente desconectado: {data['client_address']}:{data['client_port']}")
    
    elif event_type == 'FILE_RECEIVE_START':
        data = event['data']
        print(f"📥 [{timestamp}] Recibiendo archivo: {data['filename']} de {data['client']}")
    
    elif event_type == 'FILE_RECEIVE_COMPLETE':
        data = event['data']
        print(f"✅ [{timestamp}] Archivo recibido: {data['filename']} ({data['file_size']} bytes)")
    
    elif event_type == 'BLOCK_SPLIT_COMPLETE':
        data = event['data']
        print(f"🔨 [{timestamp}] Archivo dividido: {data['filename']} en {data['blocks_count']} bloques")
    
    elif event_type == 'DOWNLOAD_REQUEST':
        data = event['data']
        print(f"📤 [{timestamp}] Solicitando descarga: {data['filename']} para {data['client']}")
    
    elif event_type == 'DOWNLOAD_COMPLETE':
        data = event['data']
        print(f"✅ [{timestamp}] Descarga completada: {data['filename']} ({data['blocks_count']} bloques)")
    
    elif 'ERROR' in event_type:
        data = event['data']
        print(f"❌ [{timestamp}] ERROR: {data.get('error', 'Unknown error')}")

def main():
    # Suscribir logger
    event_manager.subscribe(server_logger)
    
    print("🚀 Iniciando Servidor DFS...")
    
    # Crear y iniciar servidor
    server = NetworkServer(host='192.168.101.9', port=8001)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        server.stop()

if __name__ == "__main__":
    main()