import unittest
from unittest.mock import patch, mock_open
from lib.ConfigManager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.config_manager = ConfigManager()

    def test_load(self):
        mock_config = """
        [Database]
        server = test_server
        database = test_db
        username = test_user
        password = test_pass

        [Printer]
        name = Test Printer

        [Settings]
        temp_folder = C:\\Temp
        check_interval = 5
        """
        with patch('builtins.open', mock_open(read_data=mock_config)):
            self.assertTrue(self.config_manager.load())

        self.assertEqual(
            self.config_manager.get_thermal_printer_name(), 'Test Printer')
        self.assertEqual(self.config_manager.get_temp_folder(), 'C:\\Temp')
        self.assertEqual(self.config_manager.get_check_interval(), 5)

    # Add more tests for other ConfigManager methods


if __name__ == '__main__':
    unittest.main()
