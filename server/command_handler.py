from core.protocol import Command
from server.file_server import FileServer
import socket

class CommandHandler:
    def __init__(self, file_server:FileServer):
        self.file_server = file_server

    def handle_command(self, client_socket: socket.socket, command: Command):
        """Despacha el comando a la función correspondiente"""
        if command == Command.UPLOAD:
            self._handle_upload(client_socket)
        elif command == Command.DOWNLOAD:
            self._handle_download(client_socket)
        elif command == Command.LIST_FILES:
            self._handle_list_files(client_socket)
        elif command == Command.DELETE:
            self._handle_delete(client_socket)
        elif command == Command.INFO:
            self._handle_info(client_socket)
        else:
            self._handle_unknown(client_socket)


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