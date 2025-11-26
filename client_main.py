import os
import sys
from client.file_client import FileClient

class ClientCLI:
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.client = FileClient(host, port)
        self.connected = False
        
    def connect_to_server(self):
        """Establece conexión con el servidor"""
        if not self.connected:
            print("Conectando al servidor...")
            if self.client.connect():
                self.connected = True
                print("Conexion establecida correctamente")
                return True
            else:
                print("No se pudo conectar al servidor")
                return False
        return True

    def disconnect_from_server(self):
        """Cierra la conexión con el servidor"""
        if self.connected:
            self.client.disconnect()
            self.connected = False
            print("Desconectado del servidor")

    def show_menu(self):
        """Muestra el menú principal"""
        print("\n" + "="*60)
        print("SISTEMA DISTRIBUIDO DE ARCHIVOS - CLIENTE")
        print("="*60)
        print("1. Subir archivo")
        print("2. Descargar archivo") 
        print("3. Eliminar archivo")
        print("4. Listar archivos disponibles")
        print("5. Obtener informacion de archivo")
        print("6. Estado del almacenamiento")
        print("7. Probar multiples operaciones")
        print("8. Salir")
        print("-"*60)

    def get_user_choice(self):
        """Obtiene la opción del usuario"""
        try:
            choice = input("Seleccione una opcion (1-8): ").strip()
            return int(choice) if choice.isdigit() else 0
        except ValueError:
            return 0

    def handle_upload(self):
        """Maneja la subida de archivos"""
        print("\n--- SUBIR ARCHIVO ---")
        file_path = input("Ruta del archivo a subir: ").strip()
        
        if not os.path.exists(file_path):
            print("ERROR: El archivo no existe")
            return
            
        if not self.connect_to_server():
            return
            
        print(f"Subiendo archivo: {file_path}")
        if self.client.upload_file(file_path):
            print("Archivo subido exitosamente")
        else:
            print("Error al subir el archivo")

    def handle_download(self):
        """Maneja la descarga de archivos"""
        print("\n--- DESCARGAR ARCHIVO ---")
        filename = input("Nombre del archivo a descargar: ").strip()
        save_dir = input("Directorio de destino (./downloads): ").strip() or "./downloads"
        
        if not self.connect_to_server():
            return
            
        print(f"Descargando: {filename} -> {save_dir}")
        if self.client.download_file(filename, save_dir):
            print("Archivo descargado exitosamente")
        else:
            print("Error al descargar el archivo")

    def handle_delete(self):
        """Maneja la eliminación de archivos"""
        print("\n--- ELIMINAR ARCHIVO ---")
        filename = input("Nombre del archivo a eliminar: ").strip()
        
        if not self.connect_to_server():
            return
            
        # Confirmación de seguridad
        confirm = input(f"Esta seguro de eliminar '{filename}'? (s/n): ").strip().lower()
        if confirm != 's':
            print("Operacion cancelada")
            return
            
        if self.client.delete_file(filename):
            print("Archivo eliminado exitosamente")
        else:
            print("Error al eliminar el archivo")

    def handle_list_files(self):
        """Maneja el listado de archivos"""
        print("\n--- LISTANDO ARCHIVOS DISPONIBLES ---")
        
        if not self.connect_to_server():
            return
            
        files = self.client.list_files()
        
        if not files:
            print("No hay archivos en el servidor")
            return
            
        print(f"\nArchivos encontrados ({len(files)}):")
        print("-" * 70)
        for i, file_info in enumerate(files, 1):
            size_mb = file_info['size'] / (1024 * 1024)
            print(f"{i:2d}. {file_info['filename']:40} {size_mb:8.2f} MB {file_info['blocks']:3d} bloques")

    def handle_file_info(self):
        """Maneja la obtención de información de archivos"""
        print("\n--- INFORMACION DE ARCHIVO ---")
        filename = input("Nombre del archivo: ").strip()
        
        if not self.connect_to_server():
            return
            
        info = self.client.get_file_info(filename)
        
        if not info:
            print("Archivo no encontrado")
            return
            
        print(f"\nInformacion de '{filename}':")
        print(f"  Tamaño: {info['size'] / (1024 * 1024):.2f} MB")
        print(f"  Bloques: {info['block_count']}")
        print(f"  Primer bloque: {info['first_block_id']}")
        print(f"  Cadena de bloques: {info['block_chain']}")

    def handle_storage_status(self):
        """Maneja la consulta del estado del almacenamiento"""
        print("\n--- ESTADO DEL ALMACENAMIENTO ---")
        
        if not self.connect_to_server():
            return
            
        status = self.client.get_storage_status()
        
        if not status:
            print("Error al obtener el estado")
            return
            
        print(f"\nEstado del sistema:")
        print(f"  Bloques totales: {status['total_blocks']}")
        print(f"  Bloques usados: {status['used_blocks']}")
        print(f"  Bloques libres: {status['free_blocks']}")
        print(f"  Uso: {status['usage_percent']:.1f}%")
        print(f"  Archivos: {status['file_count']}")
        print(f"  Espacio total usado: {status['total_files_size'] / (1024 * 1024):.2f} MB")

    def handle_multiple_operations(self):
        """Ejecuta múltiples operaciones en una sola conexión"""
        print("\n--- MULTIPLES OPERACIONES EN UNA CONEXION ---")
        
        if not self.connect_to_server():
            return
            
        try:
            print("Realizando operaciones secuenciales...")
            
            # Operación 1: Listar archivos
            print("\n1. Listando archivos...")
            files = self.client.list_files()
            print(f"   Archivos encontrados: {len(files)}")
            
            # Operación 2: Estado del almacenamiento
            print("\n2. Consultando estado...")
            status = self.client.get_storage_status()
            if status:
                print(f"   Uso del almacenamiento: {status['usage_percent']:.1f}%")
            
            # Operación 3: Subir archivo (si se especifica)
            upload_file = input("\nRuta de archivo a subir (Enter para saltar): ").strip()
            if upload_file and os.path.exists(upload_file):
                print(f"3. Subiendo {upload_file}...")
                if self.client.upload_file(upload_file):
                    print("   Subida exitosa")
                else:
                    print("   Error en subida")
            elif upload_file:
                print("   Archivo no encontrado, saltando subida...")
            
            # Operación 4: Descargar archivo (si existe)
            if files:
                download_file = input("\nNombre de archivo a descargar (Enter para saltar): ").strip()
                if download_file:
                    print(f"4. Descargando {download_file}...")
                    if self.client.download_file(download_file, "./downloads"):
                        print("   Descarga exitosa")
                    else:
                        print("   Error en descarga")
            
            print("\nTodas las operaciones completadas")
            
        except Exception as e:
            print(f"Error durante operaciones multiples: {e}")

    def run(self):
        """Ejecuta la interfaz principal"""
        print("Iniciando cliente de sistema de archivos distribuido...")
        
        while True:
            self.show_menu()
            choice = self.get_user_choice()
            
            if choice == 1:
                self.handle_upload()
            elif choice == 2:
                self.handle_download()
            elif choice == 3:
                self.handle_delete()
            elif choice == 4:
                self.handle_list_files()
            elif choice == 5:
                self.handle_file_info()
            elif choice == 6:
                self.handle_storage_status()
            elif choice == 7:
                self.handle_multiple_operations()
            elif choice == 8:
                print("\nSaliendo del sistema...")
                self.disconnect_from_server()
                break
            else:
                print("Opcion invalida. Por favor seleccione 1-8.")
            
            # Pausa antes de mostrar el menú nuevamente
            if choice != 8:
                input("\nPresione Enter para continuar...")

def main():
    """Función principal"""
    print("CLIENTE DEL SISTEMA DISTRIBUIDO DE ARCHIVOS")
    print("=" * 50)
    
    # Configuración del servidor
    host = input("Servidor [localhost]: ").strip() or "localhost"
    port_input = input("Puerto [8001]: ").strip() or "8001"
    
    try:
        port = int(port_input)
    except ValueError:
        print("Puerto invalido, usando 8001")
        port = 8001
    
    # Iniciar interfaz
    try:
        cli = ClientCLI(host, port)
        cli.run()
    except KeyboardInterrupt:
        print("\nInterrupcion por usuario")
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()