import logging
import os
import platform
import sys
# Konfiguracja logowania

def check_environment():
    """Sprawdza środowisko uruchomieniowe"""
    logging.info("=== Sprawdzanie środowiska ===")
    logging.info(f"System operacyjny: {platform.system()} {platform.release()}")
    logging.info(f"Python wersja: {sys.version}")
    logging.info(f"Katalog roboczy: {os.getcwd()}")
    logging.info(f"Ścieżka do skryptu: {os.path.abspath(__file__)}")
    return True