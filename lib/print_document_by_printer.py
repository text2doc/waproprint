import os
import logging
from lib.get_default_printer import get_default_printer
from lib.check_environment import check_environment
from lib.check_pdf_file import check_pdf_file
from lib.check_printer_queue import check_printer_queue
from lib.print_with_adobe import print_with_adobe
from lib.print_with_ghostscript import print_with_ghostscript
import win32print
import win32api
import win32con
from win32print import *
import subprocess
import time
import sys
import tempfile
import win32com.client
import platform

def print_document_by_printer(file_path, printer_name):
    """Drukuje dokument używając wskazanej drukarki"""
    try:
        logging.info(f"=== Rozpoczynam proces drukowania na drukarce: {printer_name} ===")

        # Sprawdź środowisko
        if not check_environment():
            logging.error("Środowisko nie jest poprawnie skonfigurowane")
            return False

        # Sprawdź plik PDF
        if not check_pdf_file(file_path):
            logging.error("Plik PDF nie jest dostępny lub jest uszkodzony")
            return False

        # Ustaw drukarkę jako domyślną
        win32print.SetDefaultPrinter(printer_name)
        logging.info(f"Ustawiono domyślną drukarkę: {printer_name}")

        try:
            # Konwertuj ścieżkę na absolutną
            abs_file_path = os.path.abspath(file_path)
            logging.info(f"Próba wydruku pliku: {abs_file_path}")

            # Użyj win32com do wydruku
            shell = win32com.client.Dispatch("Shell.Application")
            folder = shell.NameSpace(os.path.dirname(abs_file_path))
            item = folder.ParseName(os.path.basename(abs_file_path))

            # Wyślij do druku
            item.InvokeVerb("Print")
            logging.info(f"Wysłano dokument {abs_file_path} do druku na {printer_name}")

            # Poczekaj chwilę, aby dokument został wysłany do kolejki
            time.sleep(2)
            return True

        except Exception as e:
            logging.error(f"Błąd podczas wykonywania wydruku na {printer_name}: {str(e)}")
            return False

    except Exception as e:
        logging.error(f"Błąd podczas drukowania na {printer_name}: {str(e)}")
        return False