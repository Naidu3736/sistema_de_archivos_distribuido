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
    
    # ✅ UNA sola conexión para TODAS las operaciones
    if client.connect():
        try:
            print("🔗 Conexión establecida - Múltiples operaciones...")
            
            # Operación 1
            if client.upload_file("D:/Irvin/Documents/Manga/Vinland Saga/Vinland Saga Tomo 14.cbz"):
                print("Archivo 1 subido")
            else:
                print("Error en archivo 1")
            
            # Operación 2 - MISMA conexión
            if client.upload_file("D:/Irvin/Videos/sketchboo1.mp4"):
                print("Archivo 2 subido") 
            else:
                print("Error en archivo 2")
            
            # Operación 3 - MISMA conexión
            if client.upload_file("D:/Irvin/Videos/deseo.mp4"):
                print("Archivo 3 subido")
            else:
                print("Error en archivo 3")
            
            # Operación 4 - MISMA conexión  
            if client.download_file("deseo.mp4", "./downloads"):
                print("Descarga completada")
            else:
                print("Error en descarga")
                
        except Exception as e:
            print(f"Error general: {e}")
        finally:
            # Cerrar solo cuando terminamos TODAS las operaciones
            client.disconnect()
            print("Conexión cerrada")
    else:
        print("No se pudo conectar al servidor")

if __name__ == "__main__":
    main()