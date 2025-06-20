import os
import win32print
import win32api
import logging

import os.path
import win32print
import win32con
import win32job
import win32ui
from win32con import *
from win32api import *
from win32print import *
from lib.check_environment import check_environment


def check_pdf_file(file_path):
    """Sprawdza dostępność i poprawność pliku PDF"""
    try:
        if not os.path.exists(file_path):
            logging.error(f"Plik nie istnieje: {file_path}")
            return False

        if not os.access(file_path, os.R_OK):
            logging.error(f"Brak dostępu do pliku: {file_path}")
            return False

        # Sprawdź rozmiar pliku
        file_size = os.path.getsize(file_path)
        logging.info(f"Rozmiar pliku: {file_size} bajtów")

        # Spróbuj otworzyć plik jako PDF
        try:
            with open(file_path, 'rb') as f:
                # Sprawdź czy plik zaczyna się od sygnatury PDF
                header = f.read(4)
                if header != b'%PDF':
                    logging.error("Plik nie jest prawidłowym plikiem PDF")
                    return False
                logging.info("Plik jest prawidłowym plikiem PDF")
                return True
        except Exception as e:
            logging.error(f"Błąd podczas sprawdzania pliku PDF: {str(e)}")
            return False

    except Exception as e:
        logging.error(f"Błąd podczas sprawdzania pliku: {str(e)}")
        return False