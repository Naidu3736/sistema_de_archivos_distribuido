import signal
import sys
from server.network_server import NetworkServer
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

    def run(self):
        """Ejecuta el servidor"""
        logger.log("SYSTEM", "Iniciando Servidor DFS...")
        logger.log("SYSTEM", "Presiona Ctrl+C para detener el servidor")
        
        try:
            self.server.start()
        except Exception as e:
            logger.log("SYSTEM", f"Error iniciando servidor: {e}")
        finally:
            self.server.stop()

def main():
    server_manager = ServerManager(host='localhost', port=8001)
    server_manager.run()

if __name__ == "__main__":
    main()