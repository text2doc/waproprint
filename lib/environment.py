import os
import platform
import sys
import logging

class Environment:
    def __init__(self, logger):
        self.logger = logger
        
    def check(self):
        """Sprawdza środowisko uruchomieniowe"""
        try:
            self.logger.info("=== Sprawdzanie środowiska ===")
            self.logger.info(f"System operacyjny: {platform.system()} {platform.release()}")
            self.logger.info(f"Python wersja: {sys.version}")
            self.logger.info(f"Katalog roboczy: {os.getcwd()}")
            self.logger.info(f"Ścieżka do skryptu: {os.path.abspath(__file__)}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania środowiska: {str(e)}")
            return False 