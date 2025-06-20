import os
import subprocess
import time
import logging
from lib.check_printer_queue import check_printer_queue
from lib.wait_for_print_job import wait_for_print_job

def print_with_adobe(file_path, printer_name):
    """Drukuje dokument używając Adobe Reader"""
    adobe_paths = [
        r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd64.exe",
        r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd64.exe",
        r"C:\Program Files (x86)\Adobe\Reader\Reader\AcroRd64.exe",
        r"C:\Program Files\Adobe\Reader\Reader\AcroRd64.exe"
    ]

    abs_file_path = os.path.abspath(file_path)

    for adobe_path in adobe_paths:
        if os.path.exists(adobe_path):
            try:
                # Użyj Adobe Reader do drukowania
                cmd = f'"{adobe_path}" /t "{abs_file_path}" "{printer_name}"'
                subprocess.run(cmd, shell=True, check=True)
                logging.info(f"Wysłano dokument {abs_file_path} do druku na {printer_name} (Adobe Reader)")

                # Poczekaj chwilę, aby dokument trafił do kolejki
                time.sleep(2)

                # Sprawdź kolejkę po wysłaniu
                logging.info("Sprawdzanie kolejki drukarki po wysłaniu (Adobe Reader):")
                check_printer_queue(printer_name)

                # Poczekaj na zakończenie drukowania
                if wait_for_print_job(printer_name):
                    logging.info("Drukowanie zakończone pomyślnie")
                    return True
                else:
                    logging.error("Drukowanie nie zostało zakończone pomyślnie")
                    return False
            except Exception as e:
                logging.error(f"Błąd podczas drukowania przez Adobe Reader: {str(e)}")
            return True  # Adobe found but failed to print

    return False  # Adobe not found
