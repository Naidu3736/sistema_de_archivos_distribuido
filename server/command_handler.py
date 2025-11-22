import socket
from core.protocol import Command, Response
from server.file_server import FileServer

class CommandHandler:
    def __init__(self, file_server:FileServer):
        self.file_server = file_server

    def handle_command(self, client_socket: socket.socket, command: Command):
        """Despacha el comando a la función correspondiente"""
        try:
            if command == Command.UPLOAD:
                self.file_server.process_upload_request(client_socket)
            elif command == Command.DOWNLOAD:
                self.file_server.process_download_request(client_socket)
            elif command == Command.LIST_FILES:
                self.file_server.process_list_request(client_socket)
            elif command == Command.DELETE:
                self.file_server.process_delete_request(client_socket)
            elif command == Command.FILE_INFO:
                self.file_server.process_info_request(client_socket)
            elif command == Command.STORAGE_STATUS:
                self.file_server.process_storage_status_request(client_socket)
            elif command == Command.DISCONNECT:
                client_socket.send(Response.SUCCESS.to_bytes())
            else:
                client_socket.send(Response.INVALID_COMMAND.to_bytes())
        except Exception as e:
            print(f"Error manejando comando {command}: {str(e)}")
            client_socket.send(Response.SERVER_ERROR.to_bytes())