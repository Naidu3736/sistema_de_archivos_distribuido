# client_main_simple.py
import time
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
    print("🚀 Cliente DFS - Demo con Event Manager")
    
    # Crear cliente
    client = FileClient(host_server="192.168.101.9", port_server=8001)
    
    # Conectar al servidor
    if client.connect():
        print("✅ Conectado al servidor")
        
        # Ejemplo: Subir un archivo (simulado)
        print("\n--- SIMULANDO UPLOAD ---")
        event_manager.publish('UPLOAD_START', {
            'filename': 'mi_video.mp4', 
            'file_size': 5000000
        })
        
        # Simular progreso de upload
        for progress in [25, 50, 75, 100]:
            time.sleep(0.5)
            event_manager.publish('UPLOAD_PROGRESS', {
                'filename': 'mi_video.mp4',
                'progress': progress
            })
        
        event_manager.publish('UPLOAD_COMPLETE', {
            'filename': 'mi_video.mp4',
            'blocks_count': 5
        })
        
        time.sleep(1)
        
        # Ejemplo: Descargar un archivo (simulado)
        print("\n--- SIMULANDO DOWNLOAD ---")
        event_manager.publish('DOWNLOAD_START', {
            'filename': 'documento.pdf',
            'save_path': './descargas/'
        })
        
        # Simular recepción de bloques
        for i in range(3):
            time.sleep(0.3)
            event_manager.publish('BLOCK_RECEIVED', {
                'filename': 'documento.pdf',
                'block_name': f'block_{i+1}.bin',
                'block_index': i+1,
                'total_blocks': 3
            })
        
        event_manager.publish('FILE_RECONSTRUCTION_COMPLETE', {
            'filename': 'documento.pdf',
            'file_path': './descargas/documento.pdf'
        })
        
        event_manager.publish('DOWNLOAD_COMPLETE', {
            'filename': 'documento.pdf',
            'blocks_count': 3
        })
        
        # Desconectar
        time.sleep(1)
        client.disconnect()
        
    else:
        print("❌ No se pudo conectar al servidor")

if __name__ == "__main__":
    main()