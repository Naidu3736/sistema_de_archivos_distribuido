import socket
import os
import json
from core.protocol import Command, Response
from core.split_union import union, clean_blocks

class FileClient:
    def __init__(self, host_server: str = "0.0.0.0", port_server: int = 8001, buffer_size: int = 4096):
        self.host_server = host_server
        self.port_server = port_server
        self.BUFFER_SIZE = buffer_size
        self.temp_dir = "temp"
        self.socket = None
        os.makedirs(self.temp_dir, exist_ok=True)
        print(f"Cliente de archivos configurado - Servidor: {host_server}:{port_server}")
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host_server, self.port_server))
            
            print(f"Conectado al servidor {self.host_server}:{self.port_server}")
            return True
        except Exception as e:
            print(f"Error de conexión: {str(e)}")
            return False
        
    def upload_file(self, file_path: str):
        """Sube un archivo al dfs"""
        if not self.connect():
            return False
         
        if not os.path.exists(file_path):
            print(f"Error: Archivo no encontrado - {file_path}")
            self.disconnect()
            return False
            
        try:
            print("Iniciando subida de archivo...")
            self.socket.send(Command.UPLOAD.to_bytes())

            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            print(f"Subiendo archivo: {filename} ({file_size} bytes)")
            
            self._send_metadata_file(filename, file_size)
            self._send_content_file(file_path, file_size)
            
            response_bytes = self.socket.recv(4)
            response = Response.from_bytes(response_bytes)
            
            if response == Response.UPLOAD_COMPLETE:
                print(f"Subida completada: {filename}")
                self.disconnect()
                return True
            elif response == Response.FILE_ALREADY_EXISTS:
                print(f"Error: El archivo ya existe en el servidor - {filename}")
                self.disconnect()
                return False
            else:
                print(f"Error en subida: {response}")
                self.disconnect()
                return False
        
        except Exception as e:
            print(f"Error durante subida: {str(e)}")
            self.disconnect()
            return False    

    def download_file(self, filename: str, save_path: str):
        """Descarga un archivo del dfs"""
        if not self.connect():
            return False
            
        try:
            print(f"Solicitando descarga: {filename}")
            
            self.socket.send(Command.DOWNLOAD.to_bytes())
            
            filename_bytes = filename.encode('utf-8')
            self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
            self.socket.send(filename_bytes)
            
            response_bytes = self.socket.recv(4)
            response = Response.from_bytes(response_bytes)
            
            if response == Response.FILE_NOT_FOUND:
                print(f"Archivo no encontrado en servidor: {filename}")
                self.disconnect()
                return False
            
            elif response != Response.SUCCESS:
                print(f"Error del servidor: {response}")
                self.disconnect()
                return False
            
            print("Preparando recepción de bloques...")
            blocks_info = self._receive_blocks_info()
            
            print("Reconstruyendo archivo...")
            self._reconstruct_file(blocks_info, save_path)
            
            print("Limpiando bloques temporales...")
            self._cleanup_temp_blocks(blocks_info)
            
            response_bytes = self.socket.recv(4)
            response = Response.from_bytes(response_bytes)
            
            if response == Response.DOWNLOAD_COMPLETE:
                print(f"Descarga completada: {filename} - {len(blocks_info['blocks'])} bloques")
                self.disconnect()
                return True
            else:
                print(f"Error en descarga: {response}")
                self.disconnect()
                return False
            
        except Exception as e:
            print(f"Error durante descarga: {str(e)}")
            self.disconnect()
            return False

    def delete_file(self, filename: str):
        """Elimina un archivo del dfs"""
        if not self.connect():
            return False
            
        try:
            print(f"Solicitando eliminación: {filename}")
            
            self.socket.send(Command.DELETE.to_bytes())
            
            filename_bytes = filename.encode('utf-8')
            self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
            self.socket.send(filename_bytes)
            
            response_bytes = self.socket.recv(4)
            response = Response.from_bytes(response_bytes)
            
            if response == Response.DELETE_COMPLETE:
                print(f"Archivo eliminado: {filename}")
                self.disconnect()
                return True
            elif response == Response.FILE_NOT_FOUND:
                print(f"Archivo no encontrado: {filename}")
                self.disconnect()
                return False
            else:
                print(f"Error en eliminación: {response}")
                self.disconnect()
                return False
            
        except Exception as e:
            print(f"Error durante eliminación: {str(e)}")
            self.disconnect()
            return False

    def list_files(self):
        """Solicita lista de archivos disponibles"""
        if not self.connect():
            return []
            
        try:
            print("Solicitando lista de archivos...")
            self.socket.send(Command.LIST_FILES.to_bytes())
            
            # Recibir tamaño de la lista JSON
            size_bytes = self.socket.recv(4)
            json_size = int.from_bytes(size_bytes, 'big')
            
            # Recibir JSON con información de archivos
            json_data = b""
            while len(json_data) < json_size:
                chunk = self.socket.recv(min(self.BUFFER_SIZE, json_size - len(json_data)))
                if not chunk:
                    break
                json_data += chunk
            
            files_info = json.loads(json_data.decode('utf-8'))
            
            print(f"Lista de archivos recibida: {len(files_info)} archivos")
            
            self.disconnect()
            return files_info
            
        except Exception as e:
            print(f"Error obteniendo lista de archivos: {str(e)}")
            self.disconnect()
            return []

    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo"""
        if not self.connect():
            return None
            
        try:
            print(f"Solicitando información de: {filename}")
            
            self.socket.send(Command.FILE_INFO.to_bytes())
            
            filename_bytes = filename.encode('utf-8')
            self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
            self.socket.send(filename_bytes)
            
            # Recibir tamaño de la respuesta JSON
            size_bytes = self.socket.recv(4)
            json_size = int.from_bytes(size_bytes, 'big')
            
            # Recibir JSON con información del archivo
            json_data = b""
            while len(json_data) < json_size:
                chunk = self.socket.recv(min(self.BUFFER_SIZE, json_size - len(json_data)))
                if not chunk:
                    break
                json_data += chunk
            
            file_info = json.loads(json_data.decode('utf-8'))
            
            self.disconnect()
            return file_info
            
        except Exception as e:
            print(f"Error obteniendo información del archivo: {str(e)}")
            self.disconnect()
            return None

    def get_storage_status(self):
        """Obtiene el estado del almacenamiento del servidor"""
        if not self.connect():
            return None
            
        try:
            print("Solicitando estado del almacenamiento...")
            
            self.socket.send(Command.STORAGE_STATUS.to_bytes())
            
            # Recibir tamaño de la respuesta JSON
            size_bytes = self.socket.recv(4)
            json_size = int.from_bytes(size_bytes, 'big')
            
            # Recibir JSON con estado
            json_data = b""
            while len(json_data) < json_size:
                chunk = self.socket.recv(min(self.BUFFER_SIZE, json_size - len(json_data)))
                if not chunk:
                    break
                json_data += chunk
            
            status_info = json.loads(json_data.decode('utf-8'))
            
            self.disconnect()
            return status_info
            
        except Exception as e:
            print(f"Error obteniendo estado del almacenamiento: {str(e)}")
            self.disconnect()
            return None

    def _send_metadata_file(self, filename: str, file_size: int):
        """Envía metadata del archivo al dfs"""
        filename_bytes = filename.encode('utf-8')
        
        self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        self.socket.send(filename_bytes)
        self.socket.send(file_size.to_bytes(8, 'big'))
        
        print(f"Metadata enviada: {filename} - {file_size} bytes")
            
    def _send_content_file(self, file_path: str, file_size: int):
        """Envía el contenido del archivo al dfs"""
        filename = os.path.basename(file_path)
        print(f"Enviando contenido del archivo...")
        
        with open(file_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(self.BUFFER_SIZE)
                self.socket.send(chunk)
                bytes_sent += len(chunk)
                
                if bytes_sent % (1024 * 1024) == 0 or bytes_sent == file_size:
                    mb_sent = bytes_sent / (1024 * 1024)
                    mb_total = file_size / (1024 * 1024)
                    print(f"Progreso envío: {mb_sent:.1f} / {mb_total:.1f} MB")
    
    def _receive_blocks_info(self):
        """Recibir información de bloques del dfs"""
        print("Recibiendo información de bloques...")
        
        size_bytes = self.socket.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        sub_dir_bytes = self.socket.recv(size)
        sub_dir = sub_dir_bytes.decode('utf-8')
        
        size_bytes = self.socket.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        filename_bytes = self.socket.recv(size)
        filename = filename_bytes.decode('utf-8')
        
        size_bytes = self.socket.recv(4)
        blocks_count = int.from_bytes(size_bytes, 'big')
        
        blocks = []
        for _ in range(blocks_count):
            size_bytes = self.socket.recv(4)
            size = int.from_bytes(size_bytes, 'big')
            block_name_bytes = self.socket.recv(size)
            block_name = block_name_bytes.decode('utf-8')
            blocks.append(block_name)
            
        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks
        }
        
    def _receive_block_from_dfs(self):
        """Recibir bloques del dfs"""
        blocks_info = self._receive_blocks_info()
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        
        print(f"Recibiendo {len(blocks)} bloques: {filename}")
        
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        os.makedirs(sub_dir_path, exist_ok=True)
        
        for i, block in enumerate(blocks):
            block_size_bytes = self.socket.recv(8)
            block_size = int.from_bytes(block_size_bytes, 'big')
            
            block_path = os.path.join(sub_dir_path, block)
            
            with open(block_path, 'wb') as f:
                bytes_received = 0
                while bytes_received < block_size:
                    chunk = self.socket.recv(min(self.BUFFER_SIZE, block_size - bytes_received))
                    f.write(chunk)
                    bytes_received += len(chunk)
            
            print(f"Bloque {i+1}/{len(blocks)} recibido: {block} - {block_size} bytes")
                    
        return blocks_info
                    
    def _reconstruct_file(self, blocks_info: dict, save_path: str):
        """Unir bloques descargados del dfs"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        file_path = os.path.join(save_path, filename)
        os.makedirs(save_path, exist_ok=True)
        
        print(f"Reconstruyendo archivo desde {len(blocks)} bloques...")
        
        union(blocks, file_path, sub_dir_path)
        
        print(f"Archivo reconstruido: {file_path}")
        
    def _cleanup_temp_blocks(self, blocks_info: dict):
        """Limpia bloques temporales"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        try:
            clean_blocks(blocks, sub_dir_path)
            
            # Eliminar directorio temporal si está vacío
            if os.path.exists(sub_dir_path) and not os.listdir(sub_dir_path):
                os.rmdir(sub_dir_path)
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
            
            print(f"Bloques temporales limpiados: {len(blocks)} bloques")
        
        except Exception as e:
            print(f"Error limpiando bloques temporales: {str(e)}")
            
    def disconnect(self):
        """Cierra la conexión"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Desconectado del servidor")