# logger.py
import datetime
import os

class Logger:
    _instance = None
    _ui_callback = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Inicializa el logger"""
        self._log_entries = []
        os.makedirs("logs", exist_ok=True)
    
    def _get_log_file(self):
        """Obtiene el archivo log para la fecha actual"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        return f"./logs/{timestamp}.log"
    
    def set_ui_callback(self, callback):
        """Establece el callback para enviar logs a la UI"""
        self._ui_callback = callback
    
    def log(self, event_type, message):
        """Registra un evento en el log"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] {message}"
        
        # Agregar a memoria
        self._log_entries.append(log_entry)
        
        # Escribir en archivo
        log_file = self._get_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # Llamar callback de UI si está configurado
        if self._ui_callback:
            self._ui_callback(log_entry)
        
        # Print en consola
        print(log_entry)
    
    def get_recent_logs(self, count=10):
        """Obtiene los logs más recientes"""
        return self._log_entries[-count:] if self._log_entries else []
    
    def clear_logs(self):
        """Limpia los logs"""
        self._log_entries.clear()
        log_file = self._get_log_file()
        open(log_file, 'w').close()

# Crear instancia global
logger = Logger()