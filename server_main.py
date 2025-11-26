import signal
import sys
from server.network_server import NetworkServer
from server.nodes import node_manager
from core.logger import logger

class ServerManager:
    def __init__(self, host='localhost', port=8001):
        self.server = NetworkServer(host=host, port=port)
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales para shutdown graceful"""
        def signal_handler(sig, frame):
            logger.log("SYSTEM", f"Recibida señal {sig}. Deteniendo servidor...")
            self.server.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler) # kill command

    def configure_nodes(self):
        """Configura los nodos de almacenamiento (máximo 3)"""
        existing_nodes = node_manager.get_all_nodes()
        
        if existing_nodes:
            logger.log("SYSTEM", f"Nodos existentes cargados: {len(existing_nodes)}")
            for node in existing_nodes:
                logger.log("SYSTEM", f"  - {node['id']} (Primario: {node['max_primary_mb']}MB, Réplica: {node['max_replica_mb']}MB)")
            
            usar_existentes = input("¿Usar nodos existentes? (s/n): ").lower().strip()
            if usar_existentes == 's':
                return True
        
        print("\n" + "="*50)
        print("CONFIGURACIÓN DE NODOS DE ALMACENAMIENTO")
        print("="*50)
        print("Se pueden configurar hasta 3 nodos de almacenamiento")
        print("Cada nodo tendrá capacidad para datos primarios y réplicas")
        print("La capacidad total del sistema será la suma del espacio primario")
        print("="*50)
        
        num_nodos = 0
        while True:
            print(f"\n--- Configurando Nodo {num_nodos + 1} ---")
            
            agregar = input("¿Agregar este nodo? (s/n): ").lower().strip()
            if agregar != 's':
                break
            
            host = input("Host del nodo [localhost]: ").strip() or "localhost"
            
            try:
                port = int(input("Puerto del nodo [8002]: ").strip() or "8002")
            except ValueError:
                print("Puerto inválido, usando 8002")
                port = 8002
            
            try:
                max_primary = int(input("Capacidad primaria (MB) [100]: ").strip() or "100")
            except ValueError:
                print("Capacidad inválida, usando 100MB")
                max_primary = 100
            
            try:
                max_replica = int(input("Capacidad réplica (MB) [50]: ").strip() or "50")
            except ValueError:
                print("Capacidad inválida, usando 50MB")
                max_replica = 50
            
            # Agregar nodo
            node_id = node_manager.add_node(host, port, max_primary, max_replica)
            print(f"✅ Nodo agregado: {node_id}")
            
            num_nodos += 1
            
            if num_nodos < 3:
                continuar = input("¿Agregar otro nodo? (s/n): ").lower().strip()
                if continuar != 's':
                    break
        
        if num_nodos == 0:
            print("❌ Se requiere al menos 1 nodo para operar")
            return False
        
        # Mostrar resumen final
        total_capacity = node_manager.get_total_capacity()
        print(f"\n🎯 CONFIGURACIÓN COMPLETADA")
        print(f"   Nodos configurados: {num_nodos}")
        print(f"   Capacidad total del sistema: {total_capacity['total_capacity_mb']}MB")
        print(f"   Espacio primario total: {total_capacity['total_primary_mb']}MB")
        print(f"   Espacio réplica total: {total_capacity['total_replica_mb']}MB")
        
        return True

    def run(self):
        """Ejecuta el servidor"""
        logger.log("SYSTEM", "Iniciando Servidor DFS...")
        
        # Primero configurar nodos
        if not self.configure_nodes():
            logger.log("SYSTEM", "Configuración de nodos cancelada. Saliendo...")
            return
        
        logger.log("SYSTEM", "Presiona Ctrl+C para detener el servidor")
        
        try:
            self.server.start()
        except Exception as e:
            logger.log("SYSTEM", f"Error iniciando servidor: {e}")
        finally:
            self.server.stop()

def main():
    if len(sys.argv) > 1:
        host = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
    else:
        print("="*50)
        print("SERVIDOR DFS - SISTEMA DE ARCHIVOS DISTRIBUIDO")
        print("="*50)
        host = input("Ingrese el host del servidor [localhost]: ") or 'localhost'
        port_input = input("Ingrese el puerto del servidor [8001]: ")
        port = int(port_input) if port_input else 8001

    server_manager = ServerManager(host=host, port=port)
    server_manager.run()

if __name__ == "__main__":
    main()