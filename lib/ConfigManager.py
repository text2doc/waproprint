#!/usr/bin/env python
# -*- coding: utf-8 -*-
# lib/ConfigManager.py
"""
Skrypt monitorujący bazę danych SQL Server i automatycznie drukujący dokumenty ZO.
Monitoruje co 5 sekund nowe dokumenty i generuje wydruki PDF.
"""

import configparser
import os
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


class ConfigManager:
    """Klasa zarządzająca konfiguracją aplikacji"""

    def __init__(self, config_file=None):
        # Try to find config.ini in multiple locations
        if config_file is None:
            # 1. Check current working directory
            cwd_config = os.path.join(os.getcwd(), 'config.ini')
            # 2. Check script directory (where this file is located)
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_config = os.path.join(script_dir, 'config.ini')
            
            if os.path.exists(cwd_config):
                self.config_file = cwd_config
            elif os.path.exists(script_config):
                self.config_file = script_config
            else:
                # Default to current working directory
                self.config_file = 'config.ini'
                logger.warning(f"Using default config file path: {self.config_file}")
        else:
            self.config_file = config_file
            
        self.config = configparser.ConfigParser()
        try:
            self.load_config()
        except FileNotFoundError as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
            raise

    def load_config(self):
        """Wczytuje konfigurację z pliku"""
        # Try to find the config file in multiple locations
        if not os.path.exists(self.config_file):
            # Try to find config.ini in the same directory as this script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_config = os.path.join(script_dir, 'config.ini')
            
            if os.path.exists(script_config):
                self.config_file = script_config
                logger.info(f"Using config file from script directory: {self.config_file}")
            else:
                error_msg = f"Config file not found at any of these locations:\n"
                error_msg += f"1. {os.path.abspath(self.config_file)}\n"
                error_msg += f"2. {script_config}"
                logger.error(error_msg)
                raise FileNotFoundError(f"Plik konfiguracyjny nie został znaleziony w żadnej z lokalizacji: {error_msg}")

        # Read the config file with explicit UTF-8 encoding
        self.config.read(self.config_file, encoding='utf-8')
        logger.info(f"Wczytano konfigurację z pliku: {os.path.abspath(self.config_file)}")
        
        # Verify required sections exist
        required_sections = ['DATABASE', 'PRINTING']
        for section in required_sections:
            if section not in self.config:
                logger.warning(f"Brak wymaganej sekcji w pliku konfiguracyjnym: {section}")

    def get_connection_string(self):
        """Zwraca ciąg połączenia do bazy danych"""
        try:
            server = self.config['DATABASE']['server']
            database = self.config['DATABASE']['database']
            username = self.config['DATABASE']['username']
            password = self.config['DATABASE']['password']
            trusted_connection = self.config['DATABASE'].getboolean('trusted_connection', fallback=False)
            timeout = self.config['DATABASE'].get('timeout', fallback='30')
            encrypt = self.config['DATABASE'].get('encrypt', fallback='no')

            # Używamy Native Client zamiast standardowego sterownika SQL Server
            if trusted_connection:
                connection_string = f"DRIVER={{SQL Server Native Client 11.0}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
            else:
                connection_string = f"DRIVER={{SQL Server Native Client 11.0}};SERVER={server};DATABASE={database};UID={username};PWD={password};"

            # Dodajemy dodatkowe parametry
            connection_string += f";timeout={timeout};encrypt={encrypt};"

            logger.info(f"Wygenerowany string połączenia: {connection_string}")
            return connection_string

        except KeyError as e:
            logger.error(f"Brak wymaganego klucza w konfiguracji bazy danych: {e}")
            raise

    def get_printer_name(self):
        """Zwraca nazwę standardowej drukarki"""
        try:
            return self.config['PRINTING']['printer_name']
        except KeyError:
            logger.error("Brak nazwy drukarki w konfiguracji")
            raise

    def get_thermal_printer_name(self):
        """Zwraca nazwę drukarki termicznej"""
        try:
            return self.config['PRINTING']['thermal_printer_name']
        except KeyError:
            logger.error("Brak nazwy drukarki termicznej w konfiguracji")
            raise

    def get_thermal_printer_ip(self):
        """Zwraca adres IP drukarki termicznej sieciowej z konfiguracji"""
        try:
            return self.config['THERMAL_PRINTER'].get('ip_address', '')
        except (KeyError, AttributeError):
            logger.warning("Brak adresu IP drukarki termicznej w konfiguracji")
            return ''

    def get_thermal_printer_port(self):
        """Zwraca port drukarki termicznej sieciowej z konfiguracji"""
        try:
            return int(self.config['THERMAL_PRINTER'].get('port', 9100))
        except (KeyError, AttributeError, ValueError):
            logger.info("Używam domyślnego portu drukarki termicznej: 9100")
            return 9100

    def get_temp_folder(self):
        """Zwraca ścieżkę do folderu tymczasowego"""
        try:
            return self.config['PRINTING']['temp_folder']
        except KeyError:
            logger.error("Brak ścieżki do folderu tymczasowego w konfiguracji")
            raise

    def get_check_interval(self):
        """Zwraca interwał sprawdzania w sekundach"""
        try:
            return self.config['PRINTING'].getint('check_interval', fallback=5)
        except ValueError:
            logger.warning("Nieprawidłowa wartość interwału sprawdzania. Używam domyślnej wartości 5 sekund.")
            return 5

    def get_allowed_users(self):
        """Zwraca listę dozwolonych użytkowników"""
        try:
            users = self.config['USERS']['allowed_users']
            return [user.strip() for user in users.split(',') if user.strip()]
        except KeyError:
            logger.warning("Brak listy dozwolonych użytkowników w konfiguracji")
            return None

    def create_temp_folder(self):
        """Tworzy folder tymczasowy jeśli nie istnieje"""
        temp_folder = self.get_temp_folder()
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
            logger.info(f"Utworzono folder tymczasowy: {temp_folder}")

    def get_zo_zpl_dir(self):
        """
        Pobiera ścieżkę do katalogu z plikami ZPL z config.ini.

        Returns:
            str: Ścieżka do katalogu z plikami ZPL
        """
        try:
            return self.config.get('FILES', 'zo_zpl_dir', fallback='ZO_ZPL')
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ścieżki katalogu ZPL: {str(e)}")
            return None

    def get_printer_dpi(self):
        """
        Pobiera rozdzielczość drukarki w DPI z konfiguracji.

        Returns:
            int: Rozdzielczość drukarki w DPI
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'dpi' in self.config['THERMAL_PRINTER']:
                return self.config.getint('THERMAL_PRINTER', 'dpi', fallback=203)
            else:
                return self.config.getint('PRINTING', 'dpi', fallback=300)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania rozdzielczości drukarki: {str(e)}")
            return 203  # Domyślna rozdzielczość dla drukarek Zebra

    def get_printer_label_margin(self):
        """
        Pobiera margines etykiety z konfiguracji.

        Returns:
            float: Margines etykiety
        """
        try:
            return self.config.getfloat('PRINTING', 'label_margin', fallback=5)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania marginesu etykiety: {str(e)}")
            return 5

    def get_printer_label_width(self):
        """
        Pobiera szerokość etykiety w calach z konfiguracji.

        Returns:
            float: Szerokość etykiety w calach
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'label_width' in self.config['THERMAL_PRINTER']:
                return self.config.getfloat('THERMAL_PRINTER', 'label_width', fallback=4.0)
            else:
                return self.config.getfloat('PRINTING', 'label_width', fallback=4.0)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania szerokości etykiety: {str(e)}")
            return 4.0

    def get_printer_label_width_mm(self):
        """
        Pobiera szerokość etykiety w milimetrach z konfiguracji.

        Returns:
            float: Szerokość etykiety w milimetrach
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'label_width_mm' in self.config['THERMAL_PRINTER']:
                return self.config.getfloat('THERMAL_PRINTER', 'label_width_mm', fallback=104)
            else:
                return self.config.getfloat('PRINTING', 'label_width_mm', fallback=104)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania szerokości etykiety w mm: {str(e)}")
            return 104  # Domyślna szerokość dla drukarek termicznych 4 cale (104mm)

    def get_printer_label_height(self):
        """
        Pobiera wysokość etykiety w calach z konfiguracji.

        Returns:
            float: Wysokość etykiety w calach
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'label_height' in self.config['THERMAL_PRINTER']:
                return self.config.getfloat('THERMAL_PRINTER', 'label_height', fallback=6.0)
            else:
                return self.config.getfloat('PRINTING', 'label_height', fallback=6.0)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania wysokości etykiety: {str(e)}")
            return 6.0

    def get_printer_font_size(self):
        """
        Pobiera rozmiar czcionki z konfiguracji.

        Returns:
            int: Rozmiar czcionki
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'font_size' in self.config['THERMAL_PRINTER']:
                return self.config.getint('THERMAL_PRINTER', 'font_size', fallback=12)
            else:
                return self.config.getint('PRINTING', 'font_size', fallback=0)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania rozmiaru czcionki: {str(e)}")
            return 12

    def get_printer_encoding(self):
        """
        Pobiera kodowanie znaków z konfiguracji.

        Returns:
            str: Kodowanie znaków
        """
        try:
            # Najpierw sprawdź w sekcji THERMAL_PRINTER, potem w PRINTING
            if 'THERMAL_PRINTER' in self.config and 'encoding' in self.config['THERMAL_PRINTER']:
                return self.config.get('THERMAL_PRINTER', 'encoding', fallback='utf8')
            else:
                return self.config.get('PRINTING', 'encoding', fallback='utf8')
        except Exception as e:
            logger.error(f"Błąd podczas pobierania kodowania: {str(e)}")
            return 'utf8'

    def get_printer_folder_prefix(self):
        """
        Pobiera kodowanie znaków z konfiguracji.

        Returns:
            str: Kodowanie znaków
        """
        try:
            # Najpierw sprawdź w sekcji folder_prefix, potem w PRINTING
            return self.config.get('PRINTING', 'folder_prefix', fallback='utf8')
        except Exception as e:
            logger.error(f"Błąd podczas pobierania kodowania: {str(e)}")
            return 'utf8'

# if __name__ == "__main__":
#     config_manager = ConfigManager()
#     print("Connection string:", config_manager.get_connection_string())
#     print("Printer name:", config_manager.get_printer_name())
#     print("Temp folder:", config_manager.get_temp_folder())
#     print("Check interval:", config_manager.get_check_interval())
#     print("Allowed users:", config_manager.get_allowed_users())