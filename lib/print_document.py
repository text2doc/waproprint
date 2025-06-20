import os
import logging
from lib.get_default_printer import get_default_printer
from lib.check_environment import check_environment
from lib.check_pdf_file import check_pdf_file
from lib.check_printer_queue import check_printer_queue
from lib.print_with_adobe import print_with_adobe
from lib.print_with_ghostscript import print_with_ghostscript

def print_document(file_path):
    """Drukuje dokument używając domyślnej drukarki systemowej"""
    try:
        # Pobierz domyślną drukarkę
        printer_name = get_default_printer()
        if not printer_name:
            logging.error("Nie można pobrać domyślnej drukarki")
            return False

        logging.info(f"=== Rozpoczynam proces drukowania na domyślnej drukarce: {printer_name} ===")

        # Sprawdź środowisko
        if not check_environment():
            logging.error("Środowisko nie jest poprawnie skonfigurowane")
            return False

        # Sprawdź plik PDF
        if not check_pdf_file(file_path):
            logging.error("Plik PDF nie jest dostępny lub jest uszkodzony")
            return False

        try:
            # Konwertuj ścieżkę na absolutną
            abs_file_path = os.path.abspath(file_path)
            logging.info(f"Próba wydruku pliku: {abs_file_path}")

            # Sprawdź kolejkę przed wydrukiem
            logging.info("Sprawdzanie kolejki drukarki przed wydrukiem:")
            check_printer_queue(printer_name)

            # Spróbuj użyć Adobe Reader
            adobe_result = print_with_adobe(file_path, printer_name)

            if not adobe_result:
                logging.info("Adobe Reader nie został znaleziony, próbuję alternatywnej metody")

                # Spróbuj użyć Ghostscript
                gs_result = print_with_ghostscript(file_path, printer_name)

                if not gs_result:
                    logging.error("Nie znaleziono ani Adobe Reader, ani Ghostscript")
                    return False

                return gs_result

            return adobe_result

        except Exception as e:
            logging.error(f"Błąd podczas wykonywania wydruku: {str(e)}")
            return False

    except Exception as e:
        logging.error(f"Błąd podczas drukowania: {str(e)}")
        return False

