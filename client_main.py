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

def upload_multiple_files(client, files_to_upload):
    """Sube múltiples archivos al servidor"""
    print(f"\n--- SUBIENDO {len(files_to_upload)} ARCHIVOS ---")
    
    for i, file_info in enumerate(files_to_upload, 1):
        file_path = file_info['path']
        filename = file_info.get('name', os.path.basename(file_path))
        
        print(f"\n📁 [{i}/{len(files_to_upload)}] Procesando: {filename}")
        
        # Simular upload del archivo
        event_manager.publish('UPLOAD_START', {
            'filename': filename, 
            'file_size': file_info['size'],
            'file_index': i,
            'total_files': len(files_to_upload)
        })
        
        # Simular progreso de upload
        for progress in [10, 30, 60, 90, 100]:
            time.sleep(0.2)
            event_manager.publish('UPLOAD_PROGRESS', {
                'filename': filename,
                'progress': progress,
                'file_index': i,
                'total_files': len(files_to_upload)
            })
        
        event_manager.publish('UPLOAD_COMPLETE', {
            'filename': filename,
            'blocks_count': file_info.get('blocks', 3),
            'file_index': i,
            'total_files': len(files_to_upload)
        })
        
        time.sleep(0.5)  # Pequeña pausa entre archivos

def download_specific_file(client, filename, save_path):
    """Descarga un archivo específico del servidor"""
    print(f"\n--- DESCARGANDO ARCHIVO ESPECÍFICO ---")
    print(f"🎯 Objetivo: {filename}")
    
    # Simular descarga
    event_manager.publish('DOWNLOAD_START', {
        'filename': filename,
        'save_path': save_path
    })
    
    # Simular recepción de bloques
    blocks_count = 4  # Simular que tiene 4 bloques
    for i in range(blocks_count):
        time.sleep(0.3)
        event_manager.publish('BLOCK_RECEIVED', {
            'filename': filename,
            'block_name': f'{filename}_block_{i+1:03d}.bin',
            'block_index': i+1,
            'total_blocks': blocks_count
        })
    
    event_manager.publish('FILE_RECONSTRUCTION_COMPLETE', {
        'filename': filename,
        'file_path': os.path.join(save_path, filename)
    })
    
    event_manager.publish('DOWNLOAD_COMPLETE', {
        'filename': filename,
        'blocks_count': blocks_count
    })

def main():
    print("🚀 Cliente DFS - Múltiples Archivos")
    
    # Crear cliente
    client = FileClient(host_server="192.168.101.9", port_server=8001)
    
    # Conectar al servidor
    if client.connect():
        print("✅ Conectado al servidor")
        
        # Lista de archivos a subir
        files_to_upload = [
            {'path': '/ruta/video1.mp4', 'name': 'vacaciones.mp4', 'size': 15000000, 'blocks': 15},
            {'path': '/ruta/documento1.pdf', 'name': 'informe_final.pdf', 'size': 2500000, 'blocks': 3},
            {'path': '/ruta/imagen1.jpg', 'name': 'foto_perfil.jpg', 'size': 800000, 'blocks': 1},
            {'path': '/ruta/audio1.mp3', 'name': 'podcast_entrevista.mp3', 'size': 5000000, 'blocks': 5}
        ]
        
        # 1. Subir múltiples archivos
        upload_multiple_files(client, files_to_upload)
        
        time.sleep(1)
        
        # 2. Descargar un archivo específico de los que subimos
        file_to_download = "informe_final.pdf"  # Elegimos uno de los archivos subidos
        download_folder = "./descargas/"
        
        download_specific_file(client, file_to_download, download_folder)
        
        # 3. Opcional: Listar archivos disponibles (si implementas esta función)
        print(f"\n--- ARCHIVOS DISPONIBLES ---")
        available_files = ["vacaciones.mp4", "informe_final.pdf", "foto_perfil.jpg", "podcast_entrevista.mp3"]
        for i, filename in enumerate(available_files, 1):
            print(f"   {i}. {filename}")
        
        # Desconectar
        time.sleep(1)
        client.disconnect()
        
        print(f"\n🎯 Resumen:")
        print(f"   📤 Archivos subidos: {len(files_to_upload)}")
        print(f"   📥 Archivo descargado: {file_to_download}")
        print(f"   💾 Guardado en: {download_folder}")
        
    else:
        print("❌ No se pudo conectar al servidor")

if __name__ == "__main__":
    main()