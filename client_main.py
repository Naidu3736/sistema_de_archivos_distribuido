import os
from core.event_manager import event_manager
from client.file_client import FileClient

def main():
    client = FileClient("192.168.101.9", 8001)
    
    # UNA sola conexión para TODAS las operaciones
    if client.connect():
        try:
            print("Conexión establecida - Múltiples operaciones...")
            
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