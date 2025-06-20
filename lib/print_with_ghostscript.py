import os
import subprocess
import time
import logging
from lib.check_printer_queue import check_printer_queue
from lib.wait_for_print_job import wait_for_print_job

def print_with_ghostscript(file_path, printer_name):
    """Drukuje dokument używając Ghostscript"""
    gs_paths = [
        r"C:\Program Files\gs\gs10.05.0\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs10.05.0\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.01.5\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs10.01.5\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.01.4\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs10.01.4\bin\gswin64c.exe"
    ]

    abs_file_path = os.path.abspath(file_path)

    for gs_path in gs_paths:
        if os.path.exists(gs_path):
            try:
                # Użyj Ghostscript do drukowania
                cmd = f'"{gs_path}" -dPrinted -dBATCH -dNOPAUSE -dSAFER -sDEVICE=mswinpr2 -sOutputFile="%printer%{printer_name}" "{abs_file_path}"'
                subprocess.run(cmd, shell=True, check=True)
                logging.info(f"Wysłano dokument {abs_file_path} do druku na {printer_name} (Ghostscript)")

                # Poczekaj chwilę, aby dokument trafił do kolejki
                time.sleep(2)

                # Sprawdź kolejkę po wysłaniu
                logging.info("Sprawdzanie kolejki drukarki po wysłaniu (Ghostscript):")
                check_printer_queue(printer_name)

                # Poczekaj na zakończenie drukowania
                if wait_for_print_job(printer_name):
                    logging.info("Drukowanie zakończone pomyślnie")
                    return True
                else:
                    logging.error("Drukowanie nie zostało zakończone pomyślnie")
                    return False
            except Exception as e:
                logging.error(f"Błąd podczas drukowania przez Ghostscript: {str(e)}")
            return True  # Ghostscript found but failed to print

    return False  # Ghostscript not found
