import os
from core.event_manager import event_manager
from client.file_client import FileClient

# Consumidor simple para terminal del cliente
def simple_client_logger(event):
    event_type = event['type']
    timestamp = event['timestamp']
    
    if event_type == 'CLIENT_CONNECTED':
        data = event['data']
        print(f"🔗 [{timestamp}] Conectado al servidor {data['host']}:{data['port']}")
    
    elif event_type == 'UPLOAD_START':
        data = event['data']
        print(f"📤 [{timestamp}] Subiendo archivo: {data['filename']} ({data['file_size']} bytes)")
    
    elif event_type == 'UPLOAD_PROGRESS':
        data = event['data']
        print(f"📊 [{timestamp}] Progreso upload: {data['progress']:.1f}%")
    
    elif event_type == 'UPLOAD_COMPLETE':
        data = event['data']
        print(f"✅ [{timestamp}] Upload completado: {data['filename']} ({data['blocks_count']} bloques)")
    
    elif event_type == 'DOWNLOAD_START':
        data = event['data']
        print(f"📥 [{timestamp}] Descargando: {data['filename']} -> {data['save_path']}")
    
    elif event_type == 'BLOCK_RECEIVED':
        data = event['data']
        print(f"📦 [{timestamp}] Bloque {data['block_index']}/{data['total_blocks']} recibido: {data['block_name']}")
    
    elif event_type == 'FILE_RECONSTRUCTION_COMPLETE':
        data = event['data']
        print(f"✅ [{timestamp}] Archivo reconstruido: {data['file_path']}")
    
    elif event_type == 'DOWNLOAD_COMPLETE':
        data = event['data']
        print(f"🎉 [{timestamp}] Descarga completada: {data['filename']}")
    
    elif event_type == 'CLIENT_DISCONNECTED':
        print(f"🔌 [{timestamp}] Desconectado del servidor")
    
    elif 'ERROR' in event_type:
        data = event['data']
        print(f"❌ [{timestamp}] ERROR: {data.get('error', 'Unknown error')}")

# Suscribir el logger
event_manager.subscribe(simple_client_logger)

def main():
    client = FileClient("192.168.101.9", 8001)
    
    if not client.connect():
        return
    
    client.upload_file("D:/Irvin/Documents/Manga/Vinland Saga/Vinland Saga Tomo 14.cbz")    
    client.upload_file("D:/Irvin/Videos/sketchboo1.mp4")
    client.upload_file("D:/Irvin/Videos/deseo.mp4")
    
    client.download_file("deseo.mp4", "./downloads")

if __name__ == "__main__":
    main()