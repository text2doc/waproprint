#!/usr/bin/env python3
# lib/config.ini
import os
import configparser
import logging


class Config:
    def __init__(self, logger):
        self.logger = logger
        self.config = None

    # Poprawiona metoda load w klasie Config
    def load(self, config_path=None):
        """
        Wczytuje konfigurację z pliku config.ini

        Parametry:
            config_path (str, optional): Ścieżka do pliku konfiguracyjnego.
                                        Jeśli None, używa domyślnej ścieżki.

        Zwraca:
            bool: True jeśli wczytywanie się powiodło, False w przeciwnym razie
        """
        try:
            self.config = configparser.ConfigParser()

            # Jeśli nie podano ścieżki, użyj domyślnej
            if config_path is None:
                config_path = os.path.join(os.path.dirname(
                    os.path.abspath(__file__)), '..', 'config.ini')

            self.logger.info(f"Wczytywanie konfiguracji z: {config_path}")

            if not os.path.exists(config_path):
                self.logger.error(
                    f"Plik konfiguracyjny nie istnieje: {config_path}")
                return False

            self.config.read(config_path)
            self.logger.info("Konfiguracja wczytana pomyślnie")
            return True
        except Exception as e:
            self.logger.error(
                f"Błąd podczas wczytywania konfiguracji: {str(e)}")
            return False

    def get_printer_name(self):
        """Pobiera nazwę skonfigurowanej drukarki z config.ini"""
        try:
            if not self.config or 'PRINTING' not in self.config:
                self.logger.error(
                    "Nie znaleziono sekcji PRINTING w konfiguracji")
                return None

            printer_name = self.config['PRINTING'].get('printer_name')
            if not printer_name:
                self.logger.error(
                    "Nie znaleziono nazwy drukarki w konfiguracji")
                return None

            self.logger.info(f"Skonfigurowana drukarka: {printer_name}")
            return printer_name
        except Exception as e:
            self.logger.error(
                f"Błąd podczas pobierania skonfigurowanej drukarki: {str(e)}")
            return None

    def get_temp_folder(self):
        """Pobiera ścieżkę do folderu tymczasowego"""
        try:
            if not self.config or 'PRINTING' not in self.config:
                self.logger.error(
                    "Nie znaleziono sekcji PRINTING w konfiguracji")
                return None

            temp_folder = self.config['PRINTING'].get('temp_folder')
            if not temp_folder:
                self.logger.error(
                    "Nie znaleziono ścieżki do folderu tymczasowego w konfiguracji")
                return None

            return temp_folder
        except Exception as e:
            self.logger.error(
                f"Błąd podczas pobierania ścieżki do folderu tymczasowego: {str(e)}")
            return None

    def get_printed_folder(self):
        """Pobiera ścieżkę do folderu printed"""
        try:
            if not self.config or 'PRINTING' not in self.config:
                self.logger.error(
                    "Nie znaleziono sekcji PRINTING w konfiguracji")
                return None

            printed_folder = self.config['PRINTING'].get('printed_folder')
            if not printed_folder:
                self.logger.error(
                    "Nie znaleziono ścieżki do folderu printed w konfiguracji")
                return None

            return printed_folder
        except Exception as e:
            self.logger.error(
                f"Błąd podczas pobierania ścieżki do folderu printed: {str(e)}")
            return None

    def get_check_interval(self):
        """Pobiera interwał sprawdzania w sekundach"""
        try:
            if not self.config or 'PRINTING' not in self.config:
                self.logger.error(
                    "Nie znaleziono sekcji PRINTING w konfiguracji")
                return 5

            check_interval = self.config['PRINTING'].getint(
                'check_interval', 5)
            return check_interval
        except Exception as e:
            self.logger.error(
                f"Błąd podczas pobierania interwału sprawdzania: {str(e)}")
            return 5
