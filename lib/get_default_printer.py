import win32print
import logging

def get_default_printer():
    """Pobiera nazwę domyślnej drukarki systemowej"""
    try:
        default_printer = win32print.GetDefaultPrinter()
        logging.info(f"Domyślna drukarka systemowa: {default_printer}")
        return default_printer
    except Exception as e:
        logging.error(f"Błąd podczas pobierania domyślnej drukarki: {str(e)}")
        return None
