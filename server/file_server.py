import os
import socket
from core.split_union import split
from core.protocol import Response

class FileServer:
    def __init__(self, block_dir: str = "blocks", temp_dir: str = "temp", buffer_size: int = 4096):
        self.block_dir = block_dir
        self.temp_dir = temp_dir
        self.BUFFER_SIZE = buffer_size
        os.makedirs(block_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Servidor de archivos listo - Directorio bloques: {block_dir}, Directorio temporal: {temp_dir}")

    def process_upload_request(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente"""
        try:
            print("Iniciando recepción de archivo...")
            temp_file_path = self._receive_temp_file(client)

            print("Dividiendo archivo en bloques...")
            blocks_info = self._split_into_blocks(temp_file_path)

            print("Limpiando archivo temporal...")
            self._cleanup_temp_file(temp_file_path)

            print("Enviando confirmación al cliente...")
            client.send(Response.UPLOAD_COMPLETE.to_bytes())

            print(f"Upload completado - {len(blocks_info['blocks'])} bloques creados")
            return blocks_info
        
        except Exception as e:
            print(f"Error durante upload: {str(e)}")
            client.send(Response.SERVER_ERROR.to_bytes())
            return None

    def process_download_request(self, client: socket.socket):
        """Procesa una solicitud de download del cliente"""
        try:
            print("Solicitud de descarga recibida...")
            filename_size = int.from_bytes(client.recv(4), 'big')
            filename_bytes = client.recv(filename_size)
            filename = filename_bytes.decode('utf-8')

            print(f'Cliente solicita descarga: {filename}')

            sub_dir = os.path.splitext(filename)[0]
            blocks_dir = os.path.join(self.block_dir, sub_dir)
            
            if not os.path.exists(blocks_dir):
                print(f'Archivo no encontrado: {filename}')
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return
            
            client.send(Response.SUCCESS.to_bytes())

            blocks = [f for f in os.listdir(blocks_dir) if os.path.isfile(os.path.join(blocks_dir, f))]
            print(f"Preparando envío de {len(blocks)} bloques...")
            
            blocks_info = {
                'sub_dir': sub_dir,
                'filename': filename,
                'blocks': blocks,
                'blocks_dir': blocks_dir
            }

            self._send_blocks_to_client(client, blocks_info)

            client.send(Response.DOWNLOAD_COMPLETE.to_bytes())

            print(f'Descarga completada: {filename} - {len(blocks)} bloques enviados')

        except Exception as e:
            print(f'Error durante descarga: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _receive_temp_file(self, client: socket.socket):
        """Recibe el archivo completo del cliente"""
        print("Recibiendo información del archivo...")
        size_bytes = client.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        file_bytes = client.recv(size)
        filename = file_bytes.decode('utf-8')

        print(f'Iniciando recepción: {filename}')

        file_size_bytes = client.recv(8)
        file_size = int.from_bytes(file_size_bytes, 'big')

        os.makedirs(self.temp_dir, exist_ok=True)
        temp_file = os.path.join(self.temp_dir, filename)

        print(f"Guardando archivo: {filename} ({file_size} bytes)")
        
        with open(temp_file, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                chunk = client.recv(min(self.BUFFER_SIZE, file_size - bytes_received))
                f.write(chunk)
                bytes_received += len(chunk)

                if bytes_received % (1024 * 1024) == 0 or bytes_received == file_size:
                    mb_received = bytes_received / (1024 * 1024)
                    mb_total = file_size / (1024 * 1024)
                    print(f"Progreso: {mb_received:.1f} / {mb_total:.1f} MB")
        
        print(f"Recepción completada: {filename}")
        return temp_file
    
    def _split_into_blocks(self, file_path: str):
        """Divide el archivo en bloques"""
        filename = os.path.basename(file_path)
        print(f"Iniciando división en bloques: {filename}")

        sub_dir = os.path.splitext(filename)[0]
        sub_dir_path = os.path.join(self.block_dir, sub_dir)

        blocks = split(file_path, sub_dir_path)

        print(f'División completada: {len(blocks)} bloques creados')
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
            print(f"Archivo temporal eliminado: {temp_file_path}")
        except Exception as e:
            print(f"Error limpiando archivo temporal: {str(e)}")

    def _send_blocks_to_client(self, client: socket.socket, blocks_info: dict):
        """Envía todos los bloques al cliente"""
        sub_dir = str(blocks_info['sub_dir'])
        filename = str(blocks_info['filename'])
        blocks = list(blocks_info['blocks'])
        blocks_dir = str(blocks_info['blocks_dir'])

        print(f"Iniciando envío de bloques: {filename} - {len(blocks)} bloques")

        sub_dir_bytes = sub_dir.encode('utf-8')
        client.send(len(sub_dir_bytes).to_bytes(4, 'big'))
        client.send(sub_dir_bytes)

        filename_bytes = filename.encode('utf-8')
        client.send(len(filename_bytes).to_bytes(4, 'big'))
        client.send(filename_bytes)

        client.send(len(blocks).to_bytes(4, 'big'))

        print("Enviando bloques...")
        for i, block in enumerate(blocks):
            self._send_single_block(client, block, blocks_dir, i, len(blocks))
            print(f"Bloque {i+1}/{len(blocks)} enviado: {block}")

        print(f"Envío de bloques completado: {filename}")

    def _send_single_block(self, client: socket.socket, block_name: str, blocks_dir: str, block_index: int, total_blocks: int):
        """Envía un solo bloque al cliente"""
        block_path = os.path.join(blocks_dir, block_name)

        block_name_bytes = block_name.encode('utf-8')
        client.send(len(block_name_bytes).to_bytes(4, 'big'))
        client.send(block_name_bytes)

        block_size = os.path.getsize(block_path)
        client.send(block_size.to_bytes(8, 'big'))

        with open(block_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < block_size:
                chunk = f.read(self.BUFFER_SIZE)
                client.send(chunk)
                bytes_sent += len(chunk)

        print(f"Bloque {block_index + 1}/{total_blocks} completado: {block_name} ({block_size} bytes)")