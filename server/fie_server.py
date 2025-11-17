import os
import socket
from core.split_union import split
from core.event_manager import event_manager

class FileServer:
    def __init__(self, block_dir: str = "blocks", temp_dir: str = "temp", buffer_size: int = 4096):
        self.block_dir = block_dir
        self.temp_dir = temp_dir
        self.BUFFER_SIZE = buffer_size
        os.makedirs(block_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

    def process_upload_request(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente"""
        # Recibir archivo temporal
        temp_file_path = self._receive_temp_file(client)

        # Dividir archivo en bloques
        blocks_info = self._split_into_blocks(temp_file_path)

        # Limpiar archivo temporal
        self._cleanup_temp_file(temp_file_path)

        return blocks_info

    def process_download_request(self, client: socket.socket):
        """Procesa una solicitud de download del cliente"""
        try:
            # Recibir nombre del archivo solicitado
            filename_size = int.from_bytes(client.recv(4), 'big')
            filename_bytes = client.recv(filename_size)
            filename = filename_bytes.decode('utf-8')

            event_manager.publish('DOWNLOAD_REQUEST', {
                'filename': filename,
                'client': client.getpeername()
            })

            # Buscar archivo en el sistema
            sub_dir = os.path.splitext(filename)[0]
            blocks_dir = os.path.join(self.block_dir, sub_dir)
            
            if not os.path.exists(blocks_dir):
                event_manager.publish('DOWNLOAD_ERROR', {
                    'filename': filename,
                    'error': 'File not found',
                    'client': client.getpeername()
                })
                client.send(b"FILE_NOT_FOUND")
                return

            # Obtener lista de bloques
            blocks = [f for f in os.listdir(blocks_dir) if os.path.isfile(os.path.join(blocks_dir, f))]
            
            blocks_info = {
                'sub_dir': sub_dir,
                'filename': filename,
                'blocks': blocks,
                'blocks_dir': blocks_dir
            }

            # Enviar bloques al cliente
            self._send_blocks_to_client(client, blocks_info)

            event_manager.publish('DOWNLOAD_COMPLETE', {
                'filename': filename,
                'blocks_count': len(blocks),
                'client': client.getpeername()
            })

        except Exception as e:
            event_manager.publish('DOWNLOAD_ERROR', {
                'filename': filename,
                'error': str(e),
                'client': client.getpeername()
            })

    def _receive_temp_file(self, client: socket.socket):
        """Recibe el archivo completo del cliente"""
        # Recibir metadata
        size_bytes = client.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        file_bytes = client.recv(size)
        filename = file_bytes.decode('utf-8')

        event_manager.publish('FILE_RECEIVE_START', {
            'filename': filename,
            'client': client.getpeername()
        })

        # Recibir tamaño del archivo
        file_size_bytes = client.recv(8)
        file_size = int.from_bytes(file_size_bytes, 'big')

        # Recibir contenido del archivo
        temp_file = os.path.join(self.temp_dir, filename)

        with open(temp_file, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                progress = (bytes_received / file_size) * 100.0

                event_manager.publish('FILE_RECEIVE_PROGRESS', {
                    'filename': filename,
                    'bytes_received': bytes_received,
                    'file_size': file_size,
                    'progress': progress,
                    'client': client.getpeername()
                })

                chunk = client.recv(min(self.BUFFER_SIZE, file_size - bytes_received))
                f.write(chunk)
                bytes_received += len(chunk)
        
        event_manager.publish('FILE_RECEIVE_COMPLETE', {
            'filename': filename,
            'file_size': file_size,
            'client': client.getpeername()
        })

        return temp_file
    
    def _split_into_blocks(self, file_path: str):
        """Divide el archivo en bloques"""
        filename = os.path.basename(file_path)

        event_manager.publish('BLOCK_SPLIT_START', {
            'filename': filename,
            'file_path': file_path
        })

        sub_dir = os.path.splitext(filename)[0]
        sub_dir_path = os.path.join(self.block_dir, sub_dir)

        blocks = split(file_path, sub_dir_path)

        event_manager.publish('BLOCK_SPLIT_COMPLETE', {
            'filename': filename,
            'blocks_count': len(blocks),
            'blocks': blocks
        })

        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks,
            'blocks_dir': sub_dir_path
        }   
    
    def _cleanup_temp_file(self, temp_file_path):
        """Limpia archivos temporales"""
        try:
            os.remove(temp_file_path)
            # Si el directorio temp está vacío, eliminarlo
            temp_dir = os.path.dirname(temp_file_path)
            if not os.listdir(temp_dir):
                os.rmdir(temp_dir)
            
            event_manager.publish('TEMP_FILE_CLEANED', {
                'file_path': temp_file_path
            })
        except Exception as e:
            event_manager.publish('CLEANUP_ERROR', {
                'file_path': temp_file_path,
                'error': str(e)
            })

    def _send_blocks_to_client(self, client: socket.socket, blocks_info: dict):
        """Envía todos los bloques al cliente"""
        sub_dir = str(blocks_info['sub_dir'])
        filename = str(blocks_info['filename'])
        blocks = list(blocks_info['blocks'])
        blocks_dir = str(blocks_info['blocks_dir'])

        event_manager.publish('BLOCKS_SEND_START', {
            'filename': filename,
            'blocks_count': len(blocks),
            'client': client.getpeername()
        })

        # Enviar metadata
        # Nombre de sub-directorio
        sub_dir_bytes = sub_dir.encode('utf-8')
        client.send(len(sub_dir_bytes).to_bytes(4, 'big'))
        client.send(sub_dir_bytes)

        # Nombre de archivo
        filename_bytes = filename.encode('utf-8')
        client.send(len(filename_bytes).to_bytes(4, 'big'))
        client.send(filename_bytes)

        # Enviar número de bloques
        client.send(len(blocks).to_bytes(4, 'big'))

        # Enviar cada bloque
        for i, block in enumerate(blocks):
            self._send_single_block(client, block, blocks_dir, i, len(blocks))

        event_manager.publish('BLOCKS_SEND_COMPLETE', {
            'filename': filename,
            'blocks_count': len(blocks),
            'client': client.getpeername()
        })

    def _send_single_block(self, client: socket.socket, block_name: str, blocks_dir: str, block_index: int, total_blocks: int):
        """Envía un solo bloque al cliente"""
        block_path = os.path.join(blocks_dir, block_name)

        event_manager.publish('BLOCK_SEND_START', {
            'block_name': block_name,
            'block_index': block_index + 1,
            'total_blocks': total_blocks
        })

        # Enviar nombre del bloque
        block_name_bytes = block_name.encode('utf-8')
        client.send(len(block_name_bytes).to_bytes(4, 'big'))
        client.send(block_name_bytes)

        # Enviar tamaño del bloque
        block_size = os.path.getsize(block_path)
        client.send(block_size.to_bytes(8, 'big'))

        # Enviar contenido del bloque
        with open(block_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < block_size:
                chunk = f.read(self.BUFFER_SIZE)
                client.send(chunk)
                bytes_sent += len(chunk)

                # Publicar progreso de envío del bloque
                progress = (bytes_sent / block_size) * 100.0
                event_manager.publish('BLOCK_SEND_PROGRESS', {
                    'block_name': block_name,
                    'bytes_sent': bytes_sent,
                    'block_size': block_size,
                    'progress': progress,
                    'block_index': block_index + 1,
                    'total_blocks': total_blocks
                })

        event_manager.publish('BLOCK_SEND_COMPLETE', {
            'block_name': block_name,
            'block_size': block_size,
            'block_index': block_index + 1,
            'total_blocks': total_blocks
        })