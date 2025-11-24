from enum import Enum

class Command(Enum):
    # ===== CLIENT COMMANDS (Operaciones de usuario) =====
    UPLOAD = 1              # Iniciar subida
    DOWNLOAD = 2            # Iniciar descarga  
    LIST_FILES = 3          # Listar archivos
    DELETE = 4              # Eliminar archivo
    FILE_INFO = 5           # Info de archivo
    STORAGE_STATUS = 6      # Estado almacenamiento
    BLOCK_TABLE = 7         # Tabla de bloques
    DISCONNECT = 8          # Desconectar cliente
    
    # ===== DATA TRANSFER COMMANDS (Cliente + Nodos) =====
    GET_BLOCK = 9           # Solicitar bloque (cliente→nodo, nodo→nodo)
    SEND_BLOCK = 10         # Enviar bloque (nodo→cliente, nodo→nodo)
    
    # ===== GLOBAL COORDINATION COMMANDS =====
    METADATA_UPDATE = 11    # Actualizar metadatos
    SYNC = 12               # Sincronizar estado
    
    # ===== FUTURE: NODE MANAGEMENT COMMANDS =====
    # NODE_JOIN = 13          # Nuevo nodo se une al cluster
    # NODE_LEAVE = 14         # Nodo sale del cluster (graceful)
    # NODE_ADD = 15           # Agregar nodo a la red (de coordinador a nodos)
    # NODE_REMOVE = 16        # Remover nodo de la red (de coordinador a nodos)
    # NODE_DISCOVERY = 17     # Descubrimiento de nodos existentes
    HEARTBEAT = 18          # Latido del nodo
    # REDISTRIBUTE_DATA = 19  # Redistribuir datos
    
    # ===== NODE-TO-NODE COMMANDS =====
    REPLICATE_BLOCK = 20    # Replicar bloque
    DELETE_FILE_BLOCKS = 21 # Eliminar bloques de archivo
    # UPDATE_REPLICAS = 22    # FUTURE: Actualizar réplicas
    # NODE_STATUS_UPDATE = 23 # FUTURE: Actualizar estado de nodo

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @staticmethod
    def from_bytes(bytes_data):
        value = int.from_bytes(bytes_data, 'big')
        return Command(value)

class Response(Enum):
    # ===== CLIENT RESPONSES =====
    SUCCESS = 1
    FAILURE = 2
    UPLOAD_COMPLETE = 3
    DOWNLOAD_COMPLETE = 4
    FILE_NOT_FOUND = 5
    DELETE_COMPLETE = 6
    FILE_ALREADY_EXISTS = 7
    STORAGE_FULL = 8
    INVALID_COMMAND = 9
    SERVER_ERROR = 10
    
    # ===== DATA TRANSFER RESPONSES =====
    BLOCK_RECEIVED = 11     # Bloque recibido OK
    BLOCK_NOT_FOUND = 12    # Bloque no encontrado
    
    # ===== GLOBAL RESPONSES =====
    SYNC_COMPLETE = 13
    
    # ===== FUTURE: NODE MANAGEMENT RESPONSES =====
    # NODE_JOIN_ACCEPTED = 14 # Nodo aceptado en el cluster
    # NODE_JOIN_REJECTED = 15 # Nodo rechazado (espacio insuficiente, etc.)
    # NODE_LEAVE_ACK = 16     # Confirmación de salida de nodo
    # NODE_ADDED = 17         # Nodo agregado exitosamente
    # NODE_REMOVED = 18       # Nodo removido exitosamente
    # NODE_DISCOVERY_RESPONSE = 19 # Respuesta con lista de nodos
    HEARTBEAT_ACK = 20      # Confirmación de latido
    # REDISTRIBUTION_COMPLETE = 21 # Redistribución completada
    
    # ===== NODE-TO-NODE RESPONSES =====
    REPLICAS_UPDATED = 22
    # NODE_NOT_FOUND = 23    # FUTURE: Nodo no encontrado
    # NODE_STATUS_UPDATED = 24 # FUTURE: Estado actualizado

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @staticmethod
    def from_bytes(bytes_data):
        value = int.from_bytes(bytes_data, 'big')
        return Response(value)