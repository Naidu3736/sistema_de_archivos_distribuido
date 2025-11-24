import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.protocol import Response, Command
from server.handlers.list_handler import ListHandler
from server.handlers.storage_handler import StorageHandler
from server.handlers.info_handler import InfoHandler
from server.handlers.delete_handler import DeleteHandler
from server.handlers.block_table_handler import BlockTableHandler

class TestHandlers(unittest.TestCase):
    def setUp(self):
        self.mock_server = MagicMock()
        self.mock_client = MagicMock()
        
        # Mock locks
        self.mock_server.file_table_lock = MagicMock()
        self.mock_server.file_table_lock.__enter__ = MagicMock()
        self.mock_server.file_table_lock.__exit__ = MagicMock()
        
        self.mock_server.block_table_lock = MagicMock()
        self.mock_server.block_table_lock.__enter__ = MagicMock()
        self.mock_server.block_table_lock.__exit__ = MagicMock()

        self.mock_server.file_operation_lock = MagicMock()
        self.mock_server.file_operation_lock.__enter__ = MagicMock()
        self.mock_server.file_operation_lock.__exit__ = MagicMock()

    @patch('server.handlers.list_handler.NetworkUtils')
    def test_list_handler(self, mock_network_utils):
        handler = ListHandler(self.mock_server)
        self.mock_server.file_table.get_all_files.return_value = [{'name': 'test.txt'}]
        
        handler.process(self.mock_client)
        
        mock_network_utils.send_json.assert_called_once()
        args, _ = mock_network_utils.send_json.call_args
        self.assertEqual(args[0], self.mock_client)
        self.assertEqual(args[1], [{'name': 'test.txt'}])

    @patch('server.handlers.storage_handler.NetworkUtils')
    def test_storage_handler(self, mock_network_utils):
        handler = StorageHandler(self.mock_server)
        self.mock_server.get_storage_status.return_value = {'total': 100}
        
        handler.process(self.mock_client)
        
        mock_network_utils.send_json.assert_called_once()
        self.assertEqual(mock_network_utils.send_json.call_args[0][1], {'total': 100})

    @patch('server.handlers.info_handler.NetworkUtils')
    def test_info_handler(self, mock_network_utils):
        handler = InfoHandler(self.mock_server)
        mock_network_utils.receive_filename.return_value = 'test.txt'
        self.mock_server.get_file_info.return_value = {'name': 'test.txt'}
        
        handler.process(self.mock_client)
        
        mock_network_utils.receive_filename.assert_called_once()
        mock_network_utils.send_json.assert_called_once()

    @patch('server.handlers.delete_handler.NetworkUtils')
    def test_delete_handler(self, mock_network_utils):
        handler = DeleteHandler(self.mock_server)
        mock_network_utils.receive_filename.return_value = 'test.txt'
        self.mock_server.file_table.get_info_file.return_value = MagicMock()
        self.mock_server.file_table.name_to_id = {'test.txt': 1}
        
        handler.process(self.mock_client)
        
        mock_network_utils.receive_filename.assert_called_once()
        mock_network_utils.send_response.assert_called_with(self.mock_client, Response.DELETE_COMPLETE)

    @patch('server.handlers.block_table_handler.NetworkUtils')
    def test_block_table_handler(self, mock_network_utils):
        handler = BlockTableHandler(self.mock_server)
        self.mock_server.block_table.get_block_table.return_value = []
        
        handler.process(self.mock_client)
        
        mock_network_utils.send_json.assert_called_once()

if __name__ == '__main__':
    unittest.main()
