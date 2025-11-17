# client_main_real.py
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

def upload_multiple_files(client, files_to_upload):
    """Sube múltiples archivos REALES al servidor"""
    print(f"\n--- SUBIENDO {len(files_to_upload)} ARCHIVOS REALES ---")
    
    for i, file_info in enumerate(files_to_upload, 1):
        file_path = file_info['path']
        filename = file_info.get('name', os.path.basename(file_path))
        
        print(f"\n📁 [{i}/{len(files_to_upload)}] Procesando: {filename}")
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            print(f"❌ El archivo no existe: {file_path}")
            continue
        
        # SUBIR ARCHIVO REAL
        success = client.upload_file(file_path)
        
        if success:
            print(f"✅ Archivo subido exitosamente: {filename}")
        else:
            print(f"❌ Error subiendo archivo: {filename}")
        
        time.sleep(1)  # Pequeña pausa entre archivos

def download_specific_file(client, filename, save_path):
    """Descarga un archivo REAL del servidor"""
    print(f"\n--- DESCARGANDO ARCHIVO REAL ---")
    print(f"🎯 Objetivo: {filename}")
    
    # DESCARGAR ARCHIVO REAL
    success = client.download_file(filename, save_path)
    
    if success:
        print(f"✅ Archivo descargado exitosamente: {filename}")
    else:
        print(f"❌ Error descargando archivo: {filename}")

def main():
    print("🚀 Cliente DFS - Archivos REALES")
    
    # Crear cliente
    client = FileClient(host_server="192.168.101.9", port_server=8001)
    
    # Conectar al servidor
    if client.connect():
        print("✅ Conectado al servidor")
        
        # Lista de archivos REALES a subir
        files_to_upload = [
            {'path': 'D:/Irvin/Videos/deseo.mp4', 'name': 'deseo.mp4'},
            {'path': 'D:/Irvin/Videos/sketchboo1.mp4', 'name': 'sketchboo1.mp4'},
            {'path': 'D:/Irvin/Documents/Manga/Monster/Monster The Perfect Edition 01 (#001-016).cbr', 'name': 'monster_vol1.cbr'}
        ]
        
        # 1. Subir múltiples archivos REALES
        upload_multiple_files(client, files_to_upload)
        
        time.sleep(2)
        
        # 2. Descargar un archivo REAL de los que subimos
        file_to_download = "deseo.mp4"  # Elegimos uno de los archivos que acabamos de subir
        download_folder = "./descargas/"
        
        # Crear directorio de descargas si no existe
        os.makedirs(download_folder, exist_ok=True)
        
        download_specific_file(client, file_to_download, download_folder)
        
        # 3. Opcional: Intentar listar archivos disponibles
        print(f"\n--- INTENTANDO LISTAR ARCHIVOS ---")
        try:
            available_files = client.list_files()
            if available_files:
                print("📁 Archivos disponibles en el servidor:")
                for i, (filename, size) in enumerate(available_files, 1):
                    print(f"   {i}. {filename} ({size} bytes)")
            else:
                print("ℹ️  No se pudieron obtener archivos o la función no está implementada")
        except Exception as e:
            print(f"ℹ️  Listado de archivos no disponible: {e}")
        
        # Desconectar
        time.sleep(1)
        client.disconnect()
        
        print(f"\n🎯 Resumen REAL:")
        print(f"   📤 Archivos intentados subir: {len(files_to_upload)}")
        print(f"   📥 Archivo intentado descargar: {file_to_download}")
        print(f"   💾 Guardado en: {download_folder}")
        
        # Verificar si el archivo descargado existe
        downloaded_file = os.path.join(download_folder, file_to_download)
        if os.path.exists(downloaded_file):
            file_size = os.path.getsize(downloaded_file)
            print(f"   ✅ Archivo descargado verificado: {file_size} bytes")
        else:
            print(f"   ❌ Archivo descargado NO encontrado: {downloaded_file}")
        
    else:
        print("❌ No se pudo conectar al servidor")

if __name__ == "__main__":
    main()