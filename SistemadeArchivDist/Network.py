# Network.py

import socket
import threading
import json
import os
from PyQt5.QtCore import QThread, pyqtSignal
# Asegúrate que esta importación sea correcta (Config o sadtf_config)
from Config import BLOCK_SIZE, NODOS_CONOCIDOS 

# --- 1. Lógica del Cliente (DFSClient) ---
# (Esta clase está bien, el error no está aquí, pero la incluimos
#  para que el archivo esté completo. Es la misma de la respuesta anterior.)
class DFSClient:
    def __init__(self):
        self.timeout = 3 

    def _send_request(self, target_ip, target_port, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((target_ip, target_port))
                s.sendall(data)
                return True
        except socket.error as e:
            print(f"Error de cliente (a {target_ip}:{target_port}): {e}")
            return False

    def send_block(self, target_addr, nombre_bloque, ruta_bloque_local):
        """Envía COMANDO|NOMBRE_BLOQUE|...data..."""
        try:
            with open(ruta_bloque_local, 'rb') as f:
                block_data = f.read()
            
            # Formato: "UPLOAD_BLOCK" | "nombre_bloque|...datos_binarios..."
            header = f"UPLOAD_BLOCK".encode('utf-8')
            # El nombre del bloque AHORA es parte del payload
            payload_data = f"{nombre_bloque}".encode('utf-8') + b'|' + block_data
            
            payload = header + b'|' + payload_data
            
            return self._send_request(target_addr[0], target_addr[1], payload)
            
        except IOError as e:
            print(f"Error leyendo bloque local {ruta_bloque_local}: {e}")
            return False

    def request_block(self, target_addr, nombre_bloque):
        """Envía COMANDO|NOMBRE_BLOQUE"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect(target_addr)
                
                header = f"DOWNLOAD_BLOCK".encode('utf-8')
                payload_data = f"{nombre_bloque}".encode('utf-8')
                payload = header + b'|' + payload_data
                
                s.sendall(payload)
                
                block_data = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    block_data += chunk
                
                s.close()

                # --- CORRECCIÓN ---
                # Si el servidor envió 0 bytes (b''), lo tratamos como
                # un fallo (None) para que el cliente intente con la copia.
                if not block_data: 
                    # Eliminé la línea self.update_log(...) que causaba el crash
                    return None
                # --- FIN DE LA CORRECCIÓN ---
                
                return block_data
        except socket.error as e:
            print(f"Error solicitando bloque {nombre_bloque} de {target_addr}: {e}")
            return None
        
    def broadcast_metadata_update(self, metadata_json, remitente_addr):
        """Envía COMANDO|JSON_DATA"""
        header = f"UPDATE_METADATA".encode('utf-8')
        payload = header + b'|' + metadata_json.encode('utf-8')
        
        for nodo_addr in NODOS_CONOCIDOS.values():
            if nodo_addr != remitente_addr:
                self._send_request(nodo_addr[0], nodo_addr[1], payload)

    def send_delete_block(self, target_addr, nombre_bloque):
        """Envía COMANDO|NOMBRE_BLOQUE"""
        # Formato: "DELETE_BLOCK" | "nombre_bloque"
        header = f"DELETE_BLOCK".encode('utf-8')
        payload_data = f"{nombre_bloque}".encode('utf-8')
        payload = header + b'|' + payload_data
        
        return self._send_request(target_addr[0], target_addr[1], payload)


# --- 2. Lógica del Servidor (DFSServerThread) ---
# (Esta sección es la que contiene la corrección principal)

class DFSServerThread(QThread):
    metadata_changed = pyqtSignal()
    log_message = pyqtSignal(str)

    def __init__(self, host, port, metadata_manager):
        super().__init__()
        self.host = host
        self.port = port
        self.metadata_manager = metadata_manager
        self.is_running = True

    def run(self):
        # ... (código de 'run' sin cambios) ...
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            self.log_message.emit(f"Servidor escuchando en {self.host}:{self.port}")
        except socket.error as e:
            self.log_message.emit(f"Error al iniciar servidor: {e}")
            return

        while self.is_running:
            try:
                server_socket.settimeout(1.0) 
                conn, addr = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            except socket.timeout:
                continue 
            except socket.error as e:
                if self.is_running:
                    self.log_message.emit(f"Error de socket: {e}")
                break 
        
        server_socket.close()
        self.log_message.emit("Servidor detenido.")

    def handle_client(self, conn, addr):
        """
        Maneja la lógica de una conexión entrante.
        *** ESTA ES LA SECCIÓN CORREGIDA ***
        """
        try:
            full_data = b''
            while True:
                chunk = conn.recv(4096) 
                if not chunk:
                    break 
                full_data += chunk
            
            if not full_data:
                return

            try:
                parts = full_data.split(b'|', 1)
                header_bytes = parts[0]
                payload_bytes = parts[1] if len(parts) > 1 else b''
                command = header_bytes.decode('utf-8')
            except Exception as e:
                self.log_message.emit(f"Error de decodificación de encabezado: {e}")
                return

            # --- Lógica de Comandos (Corregida) ---
            
            if command == "UPLOAD_BLOCK":
                try:
                    nombre_bytes, block_data = payload_bytes.split(b'|', 1)
                    nombre_bloque = nombre_bytes.decode('utf-8')
                except Exception as e:
                    self.log_message.emit(f"Error parseando UPLOAD_BLOCK: {e}")
                    return
                ruta_guardado = self.metadata_manager.get_local_storage_path(nombre_bloque)
                with open(ruta_guardado, 'wb') as f:
                    f.write(block_data) 
                self.log_message.emit(f"Bloque recibido: {nombre_bloque} de {addr}")

            elif command == "DOWNLOAD_BLOCK":
                nombre_bloque = payload_bytes.decode('utf-8')
                ruta_bloque = self.metadata_manager.get_local_storage_path(nombre_bloque)
                
                if os.path.exists(ruta_bloque):
                    
                    # --- CORRECCIÓN DE DEADLOCK ---
                    # En lugar de conn.sendall(f.read()), enviamos en trozos
                    # para liberar el GIL y permitir que el hilo cliente reciba.
                    with open(ruta_bloque, 'rb') as f:
                        while True:
                            bytes_read = f.read(4096)
                            if not bytes_read:
                                break # Archivo enviado
                            conn.sendall(bytes_read)
                    # --- FIN DE LA CORRECCIÓN ---
                    
                    self.log_message.emit(f"Enviando bloque: {nombre_bloque} a {addr}")
                else:
                    self.log_message.emit(f"Petición de bloque {nombre_bloque} no encontrado.")
                    # Importante: No enviamos nada, el cliente recibirá 0 bytes

            elif command == "UPDATE_METADATA":
                metadata_json = payload_bytes.decode('utf-8')
                if self.metadata_manager.set_file_table(metadata_json):
                    self.log_message.emit(f"Metadatos sincronizados desde {addr}")
                    self.metadata_changed.emit()

            elif command == "DELETE_BLOCK":
                nombre_bloque = payload_bytes.decode('utf-8')
                ruta_bloque = self.metadata_manager.get_local_storage_path(nombre_bloque)
                if os.path.exists(ruta_bloque):
                    os.remove(ruta_bloque)
                    self.log_message.emit(f"Bloque eliminado localmente: {nombre_bloque}")
                
        except Exception as e:
            self.log_message.emit(f"Error manejando cliente {addr}: {e}")
        finally:
            conn.close() # Esto le dice al cliente que terminamos de enviar

    def stop(self):
        self.is_running = False