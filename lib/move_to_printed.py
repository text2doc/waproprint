import os
import shutil
from datetime import datetime
import logging
from lib import check_environment, check_pdf_file, check_printer_queue, get_default_printer, print_document, move_to_printed, print_with_adobe
import os
import shutil
import logging
from datetime import datetime
# Ustawienie logowania


def move_to_printed2(file_path, printed_folder):
    """Przenosi wydrukowany dokument do folderu printed"""
    try:
        # Konwertuj ścieżki na absolutne
        abs_file_path = os.path.abspath(file_path)
        abs_printed_folder = os.path.abspath(printed_folder)

        # Upewnij się, że folder printed istnieje
        if not os.path.exists(abs_printed_folder):
            os.makedirs(abs_printed_folder)
            logging.info(f"Utworzono folder: {abs_printed_folder}")

        # Generuj unikalną nazwę pliku z timestampem
        file_name = os.path.basename(abs_file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{os.path.splitext(file_name)[0]}_{timestamp}{os.path.splitext(file_name)[1]}"
        new_path = os.path.join(abs_printed_folder, new_name)

        # Przenieś plik
        shutil.move(abs_file_path, new_path)
        logging.info(f"Przeniesiono dokument do {new_path}")
        return True
    except Exception as e:
        logging.error(f"Błąd podczas przenoszenia dokumentu: {str(e)}")
        return False
