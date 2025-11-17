import socket
import os
from core.event_manager import event_manager
from core.split_union import union, clean_blocks

class FileClient:
    def __init__(self, host_server: str = "0.0.0.0", port_server: int = 8001, buffer_size: int = 4096):
        self.host_server = host_server
        self.port_server = port_server
        self.BUFFER_SIZE = buffer_size
        self.temp_dir = "temp"
        self.socket = None
        self.connected = False
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host_server, self.port_server))
            self.connected = True
            
            event_manager.publish('CLIENT_CONNECTED', {
                'host': self.host_server,
                'port': self.port_server,
                'status': 'connected'
            })
            
            return True
        except Exception as e:
            event_manager.publish('CLIENT_CONNECTION_ERROR', {
                'host': self.host_server,
                'port': self.port_server,
                'error': str(e),
                'status': 'failed'
            })
            return False
        
    def upload_file(self, file_path: str):
        """Sube un archivo al dfs"""
        if not self.connected:
            if not self.connect():
                return False
         
        if not os.path.exists(file_path):
            event_manager.publish('UPLOAD_ERROR', {
                'file_path': file_path,
                'error': 'File does not exist'
            })
            return False
            
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            event_manager.publish('UPLOAD_START', {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size
            })
            
            # Enviar metadata del archivo
            self._send_metadata_file(filename, file_size)
            
            # Enviar contenido
            self._send_content_file(file_path, file_size)
            
            # Recibir confirmación de bloques
            blocks_info = self._receive_blocks_info()
            
            event_manager.publish('UPLOAD_COMPLETE', {
                'filename': filename,
                'file_size': file_size,
                'blocks_count': len(blocks_info['blocks']),
                'blocks_info': blocks_info
            })
            
            return True
        
        except Exception as e:
            event_manager.publish('UPLOAD_ERROR', {
                'file_path': file_path,
                'error': str(e)
            })
            return False    

    def download_file(self, filename: str, save_path: str):
        """Descarga un archivo del dfs"""
        if not self.connected:
            if not self.connect():
                return False
            
        try:
            event_manager.publish('DOWNLOAD_START', {
                'filename': filename,
                'save_path': save_path
            })
            
            # Enviar solicitud de descarga (corregí el typo "DONWLOAD")
            self.socket.send(b"DOWNLOAD")
            
            # Enviar nombre del archivo
            filename_bytes = filename.encode('utf-8')
            self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
            self.socket.send(filename_bytes)
            
            # Recibir bloques del dfs
            blocks_info = self._receive_block_from_dfs()
            
            # Reconstruir archivo
            self._reconstruct_file(blocks_info, save_path)
            
            # Limpiar bloques temporales
            self._cleanup_temp_blocks(blocks_info)
            
            event_manager.publish('DOWNLOAD_COMPLETE', {
                'filename': filename,
                'save_path': save_path,
                'blocks_count': len(blocks_info['blocks'])
            })
            
            return True
            
        except Exception as e:
            event_manager.publish('DOWNLOAD_ERROR', {
                'filename': filename,
                'error': str(e)
            })
            return False

    def _send_metadata_file(self, filename: str, file_size: int):
        """Envía metadata del archivo al dfs"""
        filename_bytes = filename.encode('utf-8')
        
        # Enviar tamaño del nombre
        self.socket.send(len(filename_bytes).to_bytes(4, 'big'))
        
        # Enviar nombre
        self.socket.send(filename_bytes)
        
        # Enviar tamaño del archivo (corregí a 8 bytes para archivos grandes)
        self.socket.send(file_size.to_bytes(8, 'big'))
        
        event_manager.publish('METADATA_SENT', {
            'filename': filename,
            'file_size': file_size
        })
            
    def _send_content_file(self, file_path: str, file_size: int):
        """Envía el contenido del archivo al dfs"""
        with open(file_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(self.BUFFER_SIZE)
                self.socket.send(chunk)
                bytes_sent += len(chunk)
                
                # Publicar progreso
                progress = (bytes_sent / file_size) * 100
                event_manager.publish('UPLOAD_PROGRESS', {
                    'filename': os.path.basename(file_path),
                    'bytes_sent': bytes_sent,
                    'file_size': file_size,
                    'progress': progress
                })
    
    def _receive_blocks_info(self):
        """Recibir información de bloques del dfs"""
        # Recibir metadata de bloques
        # Nombre del sub-directorio (corregí int.to_bytes -> int.from_bytes)
        size_bytes = self.socket.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        sub_dir_bytes = self.socket.recv(size)
        sub_dir = sub_dir_bytes.decode('utf-8')
        
        # Nombre del archivo
        size_bytes = self.socket.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        filename_bytes = self.socket.recv(size)
        filename = filename_bytes.decode('utf-8')
        
        # Número de bloques
        size_bytes = self.socket.recv(4)
        blocks_count = int.from_bytes(size_bytes, 'big')
        
        blocks = []
        for _ in range(blocks_count):
            size_bytes = self.socket.recv(4)
            size = int.from_bytes(size_bytes, 'big')  # Corregí 'bit' -> 'big'
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
        
        event_manager.publish('BLOCKS_RECEIVE_START', {
            'filename': filename,
            'blocks_count': len(blocks)
        })
        
        # Crear sub-directorio temporal
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        os.makedirs(sub_dir_path, exist_ok=True)
        
        # Recibir contenido de los bloques
        for i, block in enumerate(blocks):
            # Recibir tamaño del bloque
            block_size_bytes = self.socket.recv(8)
            block_size = int.from_bytes(block_size_bytes, 'big')  # Corregí variable
            
            block_path = os.path.join(sub_dir_path, block)
            
            with open(block_path, 'wb') as f:
                bytes_received = 0
                while bytes_received < block_size:
                    chunk = self.socket.recv(min(self.BUFFER_SIZE, block_size - bytes_received))
                    f.write(chunk)
                    bytes_received += len(chunk)
            
            event_manager.publish('BLOCK_RECEIVED', {
                'filename': filename,
                'block_name': block,
                'block_size': block_size,
                'block_index': i + 1,
                'total_blocks': len(blocks)
            })
                    
        return blocks_info
                    
    def _reconstruct_file(self, blocks_info: dict, save_path: str):
        """Unir bloques descargados del dfs"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        file_path = os.path.join(save_path, filename)
        os.makedirs(save_path, exist_ok=True)
        
        event_manager.publish('FILE_RECONSTRUCTION_START', {
            'filename': filename,
            'blocks_count': len(blocks)
        })
        
        union(blocks, file_path, sub_dir_path)
        
        event_manager.publish('FILE_RECONSTRUCTION_COMPLETE', {
            'filename': filename,
            'file_path': file_path
        })
        
    def _cleanup_temp_blocks(self, blocks_info: dict):
        """Limpia bloques temporales"""
        filename = blocks_info['filename']
        sub_dir = blocks_info['sub_dir']
        blocks = blocks_info['blocks']
        sub_dir_path = os.path.join(self.temp_dir, sub_dir)
        
        try:
            clean_blocks(blocks, sub_dir_path)
            
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
            
            event_manager.publish('TEMP_BLOCKS_CLEANED', {
                'filename': filename,
                'blocks_count': len(blocks)
            })
        
        except Exception as e:
            event_manager.publish('CLEANUP_ERROR', {
                'filename': filename,
                'error': str(e)
            })
            
    def list_files(self):
        """Solicita lista de archivos disponibles"""
        if not self.connected:
            if not self.connect():
                return []
            
        try:
            self.socket.send(b"LIST_FILES")
            
            size_bytes = self.socket.recv(4)
            block_count = int.from_bytes(size_bytes, 'big')
            
            available_blocks = []  
            
            for _ in range(block_count):
                size_bytes = self.socket.recv(4)
                size = int.from_bytes(size_bytes, 'big')
                block_name_bytes = self.socket.recv(size)
                block_name = block_name_bytes.decode('utf-8')
                
                # Recibir tamaño
                size_bytes = self.socket.recv(4)
                block_size = int.from_bytes(size_bytes, 'big')
                available_blocks.append((block_name, block_size))

            event_manager.publish('FILES_LIST_RECEIVED', {
                'files_count': len(available_blocks)
            })
            
            return available_blocks
            
        except Exception as e:
            event_manager.publish('LIST_FILES_ERROR', {
                'error': str(e)
            })
            return []
    
    def disconnect(self):
        """Cierra la conexión"""
        if self.socket:
            self.socket.close()
            self.connected = False
            
            event_manager.publish('CLIENT_DISCONNECTED', {
                'host': self.host_server,
                'port': self.port_server
            })