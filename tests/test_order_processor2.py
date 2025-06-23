import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from lib.order_processor2 import process_todays_orders, DatabaseManager, ConfigManager
from lib.file_utils import get_printed_orders


class TestOrderProcessor2(unittest.TestCase):
    @patch('lib.order_processor2.ConfigManager')
    @patch('lib.order_processor2.DatabaseManager')
    def test_process_todays_orders(self, mock_db_manager, mock_config_manager):
        # Mock configuration
        mock_config = mock_config_manager.return_value
        mock_config.get_connection_string.return_value = 'test_connection_string'

        # Mock database manager
        mock_db = mock_db_manager.return_value
        mock_db.connect.return_value = True

        # Mock database query results
        mock_db.get_new_documents.return_value = [
            {
                'id': 1,
                'typ_dokumentu': 'ZO',
                'numer_dokumentu': 'ZO123456',
                'data_dokumentu': datetime.now(),
                'klient_id': 1,
                'klient_nazwa': 'Test Client',
                'klient_adres': 'Test Address',
                'klient_kod_pocztowy': '12-345',
                'klient_miasto': 'Test City',
                'operator_id': 'test_user',
                'komentarz': 'Test comment'
            }
        ]

        # Mock printed orders
        mock_get_printed_orders = Mock(return_value=set())
        with patch('lib.order_processor2.get_printed_orders', mock_get_printed_orders):
            # Test generator output
            results = list(process_todays_orders(mock_db, set()))

            # Verify results
            self.assertEqual(len(results), 1)
            order_number, html_content = results[0]
            self.assertEqual(order_number, 'ZO123456')
            self.assertIn('ZO123456', html_content)

            # Verify database calls
            mock_db.get_new_documents.assert_called_once()

    def test_main_function(self):
        # Mock main dependencies
        mock_config = Mock()
        mock_config.get_connection_string.return_value = 'test_connection_string'

        mock_db_manager = Mock()
        mock_db_manager.connect.return_value = True

        mock_process_todays_orders = Mock()
        mock_process_todays_orders.return_value = [
            ('ZO123456', '<html>Test</html>')]

        # Mock file operations
        mock_open = Mock()
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Test main function
        with patch('lib.order_processor2.ConfigManager', return_value=mock_config), \
                patch('lib.order_processor2.DatabaseManager', return_value=mock_db_manager), \
                patch('lib.order_processor2.process_todays_orders', mock_process_todays_orders), \
                patch('lib.order_processor2.get_zo_html_dir', return_value='/test/html'), \
                patch('lib.order_processor2.get_path_order', return_value='/test/html/ZO123456.html'), \
                patch('builtins.open', mock_open):

            from lib.order_processor2 import main
            main()

            # Verify file operations
            mock_open.assert_called_once_with(
                '/test/html/ZO123456.html', 'w', encoding='utf-8')
            mock_file.write.assert_called_once_with('<html>Test</html>')


if __name__ == '__main__':
    unittest.main()
