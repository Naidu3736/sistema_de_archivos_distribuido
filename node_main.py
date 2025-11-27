# nodes/storage_node_main.py
import sys
import signal
from nodes.storage_node import StorageNode
from core.logger import logger

class StorageNodeManager:
    def __init__(self, host='localhost', port=8002, storage_dir="blocks", capacity_mb=500):
        self.node = StorageNode(
            host=host, 
            port=port, 
            storage_base_dir=storage_dir,
            capacity_mb=capacity_mb
        )
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales para shutdown graceful"""
        def signal_handler(sig, frame):
            logger.log("STORAGE_NODE", f"Recibida señal {sig}. Deteniendo nodo...")
            self.node.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler) # kill command

    def run(self):
        """Ejecuta el nodo de almacenamiento"""
        logger.log("STORAGE_NODE", f"Iniciando Nodo de Almacenamiento...")
        logger.log("STORAGE_NODE", f"Host: {self.node.host}")
        logger.log("STORAGE_NODE", f"Puerto: {self.node.port}")
        logger.log("STORAGE_NODE", f"Directorio: {self.node.storage_base_dir}")
        logger.log("STORAGE_NODE", f"Capacidad: {self.node.capacity_mb}MB")
        logger.log("STORAGE_NODE", "Presiona Ctrl+C para detener el nodo")
        
        try:
            self.node.start()
        except Exception as e:
            logger.log("STORAGE_NODE", f"Error iniciando nodo: {e}")
        finally:
            self.node.stop()

def main():
    print("="*50)
    print("NODO DE ALMACENAMIENTO DFS")
    print("="*50)
    
    # Configuración interactiva
    host = input("Ingrese el host del nodo [localhost]: ").strip() or 'localhost'
    
    port_input = input("Ingrese el puerto del nodo [8002]: ").strip()
    port = int(port_input) if port_input else 8002
    
    storage_dir = input("Ingrese el directorio de almacenamiento [blocks]: ").strip() or 'blocks'
    
    capacity_input = input("Ingrese la capacidad en MB [500]: ").strip()
    capacity_mb = int(capacity_input) if capacity_input else 500
    
    # Crear nombre único para el directorio basado en el puerto
    storage_dir = f"{storage_dir}_{port}"
    
    print("\n" + "="*50)
    print("CONFIGURACIÓN DEL NODO:")
    print(f"  Host: {host}")
    print(f"  Puerto: {port}")
    print(f"  Directorio: {storage_dir}")
    print(f"  Capacidad: {capacity_mb}MB")
    print("="*50)
    
    confirm = input("\n¿Iniciar nodo con esta configuración? (s/n): ").lower().strip()
    if confirm != 's':
        print("Configuración cancelada.")
        return
    
    node_manager = StorageNodeManager(
        host=host,
        port=port, 
        storage_dir=storage_dir,
        capacity_mb=capacity_mb
    )
    node_manager.run()

if __name__ == "__main__":
    main()