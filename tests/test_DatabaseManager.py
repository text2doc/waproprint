import unittest
from unittest.mock import Mock, patch
from lib.DatabaseManager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.connection_string = 'test_connection_string'
        self.db_manager = DatabaseManager(self.connection_string)

    def test_connect_success(self):
        with patch('pyodbc.connect') as mock_connect:
            mock_connect.return_value = Mock()
            result = self.db_manager.connect()
            self.assertTrue(result)
            mock_connect.assert_called_once_with(self.connection_string)

    def test_connect_failure(self):
        with patch('pyodbc.connect') as mock_connect:
            mock_connect.side_effect = Exception('Connection error')
            result = self.db_manager.connect()
            self.assertFalse(result)

    def test_close(self):
        self.db_manager.connection = Mock()
        self.db_manager.close()
        self.db_manager.connection.close.assert_called_once()

    def test_get_new_documents(self):
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock query results
        mock_cursor.fetchall.return_value = [
            (1, 'ZO', 'ZO123456', 1, 'Test Client', 'Test Address',
             '12-345', 'Test City', 'test_user', 'Test comment')
        ]

        with patch('pyodbc.connect', return_value=mock_conn):
            documents = self.db_manager.get_new_documents(['test_user'])

            self.assertEqual(len(documents), 1)
            doc = documents[0]
            self.assertEqual(doc['id'], 1)
            self.assertEqual(doc['number'], 'ZO123456')
            self.assertEqual(doc['customer_name'], 'Test Client')

    def test_get_new_documents_no_users(self):
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('pyodbc.connect', return_value=mock_conn):
            documents = self.db_manager.get_new_documents(None)

            # Verify user filter wasn't applied
            query = mock_cursor.execute.call_args[0][0]
            self.assertNotIn('AND op.KOD IN', query)


if __name__ == '__main__':
    unittest.main()
