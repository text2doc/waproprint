import os
import shutil
import time
import logging
from datetime import datetime

def move_to_printed(file_path, max_attempts=5, delay=1):
    """
    Przenosi wydrukowany dokument do folderu printed z obsługą zajętych plików.

    Args:
        file_path: Ścieżka do pliku do przeniesienia
        max_attempts: Maksymalna liczba prób przeniesienia pliku
        delay: Opóźnienie w sekundach między próbami
    """
    try:
        # Użyj folderu printed w tym samym katalogu co skrypt
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        printed_folder = os.path.join(script_dir, 'printed')

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

        # Próbuj przenieść plik z obsługą zajętych plików
        attempt = 0
        success = False

        while attempt < max_attempts and not success:
            try:
                shutil.move(abs_file_path, new_path)
                logging.info(f"Przeniesiono dokument do {new_path}")
                success = True
            except PermissionError as e:
                attempt += 1
                logging.warning(
                    f"Plik jest używany przez inny proces. Próba {attempt}/{max_attempts}. Czekam {delay}s...")
                time.sleep(delay)
            except Exception as e:
                logging.error(f"Nieoczekiwany błąd podczas przenoszenia pliku: {str(e)}")
                return False

        if not success:
            logging.error(f"Nie udało się przenieść pliku po {max_attempts} próbach")
            return False

        return True
    except Exception as e:
        logging.error(f"Błąd podczas przenoszenia dokumentu: {str(e)}")
        return False