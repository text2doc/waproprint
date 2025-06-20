import win32print
import logging

def set_default_printer(printer_name):
    """Ustawia wskazaną drukarkę jako domyślną w systemie"""
    try:
        win32print.SetDefaultPrinter(printer_name)
        logging.info(f"Ustawiono drukarkę {printer_name} jako domyślną")
        return True
    except Exception as e:
        logging.error(f"Błąd podczas ustawiania drukarki domyślnej: {str(e)}")
        return False
