# core/protocol.py (VERSIÓN SIMPLIFICADA)
from enum import Enum

class Command(Enum):
    # Comandos del cliente al servidor principal
    UPLOAD = 1
    DOWNLOAD = 2
    DELETE = 3
    LIST = 4
    INFO = 5
    STORAGE_STATUS = 6
    BLOCK_TABLE = 7
    DISCONNECT = 8
    
    # Comandos del servidor a nodos de almacenamiento
    UPLOAD_BLOCK = 9
    DOWNLOAD_BLOCK = 10
    DELETE_BLOCK = 11
    PING = 12

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @classmethod
    def from_bytes(cls, data):
        if len(data) < 4:
            raise ValueError("Datos insuficientes para comando")
        value = int.from_bytes(data, byteorder='big')
        return cls(value)

class Response(Enum):
    SUCCESS = 1
    ERROR = 2
    FILE_NOT_FOUND = 3
    STORAGE_FULL = 4
    UPLOAD_COMPLETE = 5
    DOWNLOAD_COMPLETE = 6
    DELETE_COMPLETE = 7
    SERVER_ERROR = 8
    FILE_ALREADY_EXISTS = 9

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @classmethod
    def from_bytes(cls, data):
        if len(data) < 4:
            raise ValueError("Datos insuficientes para respuesta")
        value = int.from_bytes(data, byteorder='big')
        return cls(value)