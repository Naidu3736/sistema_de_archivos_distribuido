from enum import Enum

class Command(Enum):
    UPLOAD = 1
    DOWNLOAD = 2
    LIST_FILES = 3
    DELETE = 4
    INFO = 5

    def to_bytes(self):
        return self.value.to_bytes(4, 'big')
    
    @staticmethod
    def from_bytes(bytes_data):
        value = int.from_bytes(bytes_data, 'big')

        return Command(value)