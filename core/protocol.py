from enum import Enum

class Command(Enum):
    UPLOAD = 1
    DOWNLOAD = 2
    LIST_FILES = 3
    DELETE = 4
    FILE_INFO = 5
    STORAGE_STATUS = 6

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @staticmethod
    def from_bytes(bytes_data):
        value = int.from_bytes(bytes_data, 'big')
        return Command(value)

class Response(Enum):
    SUCCESS = 1
    FAILURE = 2
    UPLOAD_COMPLETE = 3
    DOWNLOAD_COMPLETE = 4
    FILE_NOT_FOUND = 5
    INVALID_COMMAND = 6
    SERVER_ERROR = 7
    DELETE_COMPLETE = 8
    FILE_ALREADY_EXISTS = 9
    
    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @staticmethod
    def from_bytes(bytes_data):
        value = int.from_bytes(bytes_data, 'big')
        return Response(value)