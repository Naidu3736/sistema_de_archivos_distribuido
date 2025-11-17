from core.protocol import Command
from server.file_server import FileServer
import socket

class CommandHandler:
    def __init__(self, file_server:FileServer):
        self.file_server = file_server

    def handle_command(self, client_socket:socket.socket, command:Command):
        """ Despacha el comando a la función correspondiente """
        if command == Command.UPLOAD:
            pass
        elif command == Command.DOWNLOAD:
            pass
        elif command == Command.LIST_FILES:
            pass
        elif command == Command.DELETE:
            pass
        elif command == Command.INFO:
            pass
        else:
            pass


    def _handle_upload(self, client_socke:socket.socket):
        """ Logica específica para upload """
        # Procesar solicitud
        self.file_server.process_upload_request(client_socke)

    def _handle_download(self, client_socket:socket.socket):
        """ Lógicas específica para download """
        # Procesar solicitud
        self.file_server.process_download_request(client_socket)

    def _handle_list_files(self, client_socket:socket.socket):
        pass

    def _handle_delete(self, client_socket:socket.socket):
        pass

    def _handle_info(self, client_socket:socket.socket):
        pass

    def _handle_unknown(self, client_socket:socket.socket):
        pass