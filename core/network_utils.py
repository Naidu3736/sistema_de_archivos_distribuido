import os
import socket
import json
import struct
from typing import Any, Dict, Optional, Union
from core.protocol import Command, Response

class NetworkUtils:
    """Utilidades compartidas para comunicación de red"""
    
    BUFFER_SIZE = 4096

    @staticmethod
    def send_command(socket: socket.socket, command: Command):
        """Envía un comando al socket"""
        socket.send(command.to_bytes())

    @staticmethod
    def send_response(socket: socket.socket, response: Response):
        """Envía una respuesta al socket"""
        socket.send(response.to_bytes())

    @staticmethod
    def receive_command(socket: socket.socket) -> Command:
        """Recibe un comando del socket"""
        cmd_bytes = socket.recv(4)
        return Command.from_bytes(cmd_bytes)

    @staticmethod
    def receive_response(socket: socket.socket) -> Response:
        """Recibe una respuesta del socket"""
        res_bytes = socket.recv(4)
        return Response.from_bytes(res_bytes)

    @staticmethod
    def send_json(socket: socket.socket, data: Dict[str, Any]):
        """Envía un diccionario como JSON"""
        json_data = json.dumps(data).encode('utf-8')
        socket.send(len(json_data).to_bytes(4, 'big'))
        socket.send(json_data)

    @staticmethod
    def receive_json(socket: socket.socket) -> Dict[str, Any]:
        """Recibe y decodifica un JSON"""
        size_bytes = socket.recv(4)
        if not size_bytes:
            return {}
        json_size = int.from_bytes(size_bytes, 'big')
        json_data = NetworkUtils.receive_complete_data(socket, json_size)
        return json.loads(json_data.decode('utf-8'))

    @staticmethod
    def receive_complete_data(socket: socket.socket, total_size: int) -> bytes:
        """Recibe exactamente total_size bytes"""
        data = b""
        while len(data) < total_size:
            chunk_size = min(NetworkUtils.BUFFER_SIZE, total_size - len(data))
            chunk = socket.recv(chunk_size)
            if not chunk:
                break
            data += chunk
        return data

    @staticmethod
    def send_complete_data(socket: socket.socket, data: bytes):
        """Envía todos los datos garantizando la entrega completa"""
        total_sent = 0
        while total_sent < len(data):
            sent = socket.send(data[total_sent:])
            if sent == 0:
                raise RuntimeError("Conexión interrumpida")
            total_sent += sent

    @staticmethod
    def send_filename(socket: socket.socket, filename: str):
        """Envía un nombre de archivo"""
        filename_bytes = filename.encode('utf-8')
        socket.send(len(filename_bytes).to_bytes(4, 'big'))
        socket.send(filename_bytes)

    @staticmethod
    def receive_filename(socket: socket.socket) -> str:
        """Recibe un nombre de archivo"""
        size_bytes = socket.recv(4)
        if not size_bytes:
            return ""
        filename_size = int.from_bytes(size_bytes, 'big')
        filename_bytes = socket.recv(filename_size)
        return filename_bytes.decode('utf-8')

    @staticmethod
    def send_file_size(socket: socket.socket, file_size: int):
        """Envía el tamaño de un archivo (8 bytes)"""
        socket.send(file_size.to_bytes(8, 'big'))

    @staticmethod
    def receive_file_size(socket: socket.socket) -> int:
        """Recibe el tamaño de un archivo (8 bytes)"""
        size_bytes = socket.recv(8)
        return int.from_bytes(size_bytes, 'big')

    @staticmethod
    def send_file_metadata(socket: socket.socket, filename: str, file_size: int):
        """Envía metadatos de archivo (nombre y tamaño)"""
        NetworkUtils.send_filename(socket, filename)
        NetworkUtils.send_file_size(socket, file_size)

    @staticmethod
    def send_string(socket: socket.socket, text: str):
        """Envía una cadena de texto"""
        text_bytes = text.encode('utf-8')
        socket.send(len(text_bytes).to_bytes(4, 'big'))
        socket.send(text_bytes)

    @staticmethod
    def receive_string(socket: socket.socket) -> str:
        """Recibe una cadena de texto"""
        size_bytes = socket.recv(4)
        if not size_bytes:
            return ""
        text_size = int.from_bytes(size_bytes, 'big')
        text_bytes = socket.recv(text_size)
        return text_bytes.decode('utf-8')

    @staticmethod
    def send_int(socket: socket.socket, number: int):
        """Envía un entero (4 bytes)"""
        socket.send(number.to_bytes(4, 'big'))

    @staticmethod
    def receive_int(socket: socket.socket) -> int:
        """Recibe un entero (4 bytes)"""
        int_bytes = socket.recv(4)
        return int.from_bytes(int_bytes, 'big')

    @staticmethod
    def send_bool(socket: socket.socket, value: bool):
        """Envía un valor booleano (1 byte)"""
        socket.send(b'\x01' if value else b'\x00')

    @staticmethod
    def receive_bool(socket: socket.socket) -> bool:
        """Recibe un valor booleano (1 byte)"""
        bool_byte = socket.recv(1)
        return bool_byte == b'\x01'

    @staticmethod
    def send_file_chunked(socket: socket.socket, file_path: str, chunk_size: int = BUFFER_SIZE):
        """Envía un archivo en chunks para manejar archivos grandes"""
        file_size = os.path.getsize(file_path)
        NetworkUtils.send_file_size(socket, file_size)
        
        with open(file_path, 'rb') as file:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                NetworkUtils.send_complete_data(socket, chunk)
                bytes_sent += len(chunk)

    @staticmethod
    def receive_file_chunked(socket: socket.socket, file_path: str, chunk_size: int = BUFFER_SIZE):
        """Recibe un archivo en chunks para manejar archivos grandes"""
        file_size = NetworkUtils.receive_file_size(socket)
        
        with open(file_path, 'wb') as file:
            bytes_received = 0
            while bytes_received < file_size:
                remaining = file_size - bytes_received
                chunk = socket.recv(min(chunk_size, remaining))
                if not chunk:
                    break
                file.write(chunk)
                bytes_received += len(chunk)