import unittest
from unittest.mock import patch, Mock
import sys

if sys.platform == 'win32':
    from lib.MonitorService import MonitorService
else:
    # Mock MonitorService for non-Windows platforms
    class MonitorService:
        def __init__(self):
            pass

        def load_config(self):
            return True

        def check_and_print_orders(self):
            return True

        def run(self):
            return True


class TestMonitorService(unittest.TestCase):
    def setUp(self):
        self.monitor_service = MonitorService()

    @patch('lib.DatabaseManager.DatabaseManager')
    @patch('lib.DocumentProcessor.DocumentProcessor')
    @patch('lib.printer.Printer.print_file')
    @patch.object(MonitorService, 'check_and_print_orders')
    def test_check_and_print_orders(self, mock_check_and_print, mock_print, mock_doc_processor, mock_db_manager):
        mock_db_manager.execute_query.return_value = [('ZO001',), ('ZO002',)]
        mock_doc_processor.generate_pdf.return_value = 'test.pdf'

        self.monitor_service.check_and_print_orders()

        self.assertEqual(mock_db_manager.execute_query.call_count, 1)
        self.assertEqual(mock_doc_processor.generate_pdf.call_count, 2)
        self.assertEqual(mock_print.call_count, 2)
        mock_check_and_print.assert_called_once()

    @patch('lib.ConfigManager.ConfigManager')
    def test_load_config(self, mock_config_manager):
        mock_config = {
            'database': {'connection_string': 'test_connection_string'},
            'printer': {'name': 'test_printer'},
            'monitoring': {'interval': '10'}
        }
        mock_config_manager.return_value.get_config.return_value = mock_config

        self.monitor_service.load_config()

        self.assertEqual(
            self.monitor_service.db_connection_string, 'test_connection_string')
        self.assertEqual(self.monitor_service.printer_name, 'test_printer')
        self.assertEqual(self.monitor_service.monitoring_interval, 10)

    @patch('time.sleep')
    @patch.object(MonitorService, 'check_and_print_orders')
    def test_run(self, mock_check_and_print, mock_sleep):
        self.monitor_service.monitoring_interval = 5
        mock_check_and_print.side_effect = [
            None, None, Exception("Test exception"), KeyboardInterrupt]

        with self.assertRaises(KeyboardInterrupt):
            self.monitor_service.run()

        self.assertEqual(mock_check_and_print.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_called_with(5)


if __name__ == '__main__':
    unittest.main()
