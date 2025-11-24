import socket
from core.protocol import Command, Response
from core.network_utils import NetworkUtils

class CommandHandler:
    def __init__(self, file_server):
        self.file_server = file_server

    def handle_command(self, client: socket.socket, command: Command):
        """Despacha el comando a la función correspondiente"""
        try:
            if command == Command.UPLOAD:
                self.file_server.process_upload_request(client)
            elif command == Command.DOWNLOAD:
                self.file_server.process_download_request(client)
            elif command == Command.LIST_FILES:
                self.file_server.process_list_request(client)
            elif command == Command.DELETE:
                self.file_server.process_delete_request(client)
            elif command == Command.FILE_INFO:
                self.file_server.process_info_request(client)
            elif command == Command.STORAGE_STATUS:
                self.file_server.process_storage_status_request(client)
            elif command == Command.BLOCK_TABLE:
                self.file_server.process_block_table_request(client)
            elif command == Command.DISCONNECT:
                NetworkUtils.send_response(client, Response.SUCCESS)
            else:
                NetworkUtils.send_response(client, Response.INVALID_COMMAND)
        except Exception as e:
            print(f"Error manejando comando {command}: {str(e)}")
            NetworkUtils.send_response(client, Response.SERVER_ERROR)