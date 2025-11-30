from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import logger

class ConnectionThread(QThread):
    """
    Hilo para manejar la conexión al servidor de forma asíncrona
    y evitar congelar la interfaz gráfica.
    """
    connection_success = pyqtSignal()
    connection_failed = pyqtSignal()
    connection_error = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        try:
            logger.log("GUI", f"Intentando conectar a {self.client.host_server}:{self.client.port_server}...")
            if self.client.connect():
                self.connection_success.emit()
            else:
                self.connection_failed.emit()
        except Exception as e:
            logger.log("GUI", f"Excepción en hilo de conexión: {str(e)}")
            self.connection_error.emit(str(e))
