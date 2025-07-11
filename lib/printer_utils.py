import win32print
import time
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


def check_printer_queue(printer_name):
    """Sprawdza kolejkę drukarki i zwraca informacje o zadaniach"""
    try:
        # Pobierz uchwyt do drukarki
        printer_handle = win32print.OpenPrinter(printer_name)
        if not printer_handle:
            logging.error(f"Nie można otworzyć drukarki: {printer_name}")
            return False

        # Pobierz informacje o zadaniach
        jobs = []
        job_info = win32print.EnumJobs(printer_handle, 0, -1, 2)

        if job_info:
            for job in job_info:
                jobs.append({
                    'job_id': job['JobId'],
                    'status': job['Status'],
                    'document_name': job['pDocument'],
                    'printer_name': job['pPrinterName'],
                    'user_name': job['pUserName']
                })
                logging.info(
                    f"Zadanie w kolejce: ID={job['JobId']}, Status={job['Status']}, Dokument={job['pDocument']}")
        else:
            logging.info("Kolejka drukarki jest pusta")

        # Zamknij uchwyt do drukarki
        win32print.ClosePrinter(printer_handle)
        return True
    except Exception as e:
        logging.error(f"Błąd podczas sprawdzania kolejki drukarki: {str(e)}")
        return False


def wait_for_print_job(printer_name, timeout=30):
    """Czeka na zakończenie zadania drukowania"""
    try:
        start_time = time.time()
        job_found = False

        while time.time() - start_time < timeout:
            # Sprawdź kolejkę
            printer_handle = win32print.OpenPrinter(printer_name)
            if not printer_handle:
                logging.error(f"Nie można otworzyć drukarki: {printer_name}")
                return False

            jobs = win32print.EnumJobs(printer_handle, 0, -1, 2)
            win32print.ClosePrinter(printer_handle)

            if jobs:
                job_found = True
                for job in jobs:
                    status_text = []
                    if job['Status'] & win32print.JOB_STATUS_PRINTING:
                        status_text.append("DRUKOWANIE")
                    if job['Status'] & win32print.JOB_STATUS_ERROR:
                        status_text.append("BŁĄD")
                    if job['Status'] & win32print.JOB_STATUS_OFFLINE:
                        status_text.append("DRUKARKA OFFLINE")
                    if job['Status'] & win32print.JOB_STATUS_PAPEROUT:
                        status_text.append("BRAK PAPIERU")
                    if job['Status'] & win32print.JOB_STATUS_PRINTED:
                        status_text.append("WYDRUKOWANO")
                    if job['Status'] & win32print.JOB_STATUS_DELETED:
                        status_text.append("USUNIĘTO")
                    if job['Status'] & win32print.JOB_STATUS_BLOCKED_DEVQ:
                        status_text.append("ZABLOKOWANO")
                    if job['Status'] & win32print.JOB_STATUS_USER_INTERVENTION:
                        status_text.append("WYMAGA INTERWENCJI UŻYTKOWNIKA")
                    if job['Status'] & win32print.JOB_STATUS_RESTART:
                        status_text.append("WYMAGA RESTARTU")
                    if job['Status'] & win32print.JOB_STATUS_COMPLETE:
                        status_text.append("ZAKOŃCZONO")
                    if job['Status'] & win32print.JOB_STATUS_RETAINED:
                        status_text.append("ZATRZYMANO")
                    if job['Status'] & win32print.JOB_STATUS_RENDERING_LOCALLY:
                        status_text.append("PRZYGOTOWYWANIE DO DRUKU")

                    status_str = " | ".join(
                        status_text) if status_text else "BRAK STATUSU"
                    logging.info(
                        f"Status zadania {job['JobId']}: {status_str}")
                    logging.info(
                        f"Szczegóły zadania: Dokument={job['pDocument']}, Użytkownik={job['pUserName']}")

                    if job['Status'] & win32print.JOB_STATUS_ERROR:
                        logging.error(f"Błąd w zadaniu {job['JobId']}")
                        return False
                    elif job['Status'] & win32print.JOB_STATUS_COMPLETE:
                        logging.info(
                            f"Zadanie {job['JobId']} zostało zakończone pomyślnie")
                        return True
            elif job_found:
                logging.info("Zadanie zostało usunięte z kolejki")
                return True

            time.sleep(1)  # Poczekaj 1 sekundę przed następnym sprawdzeniem

        logging.warning(
            "Przekroczono czas oczekiwania na zakończenie drukowania")
        return False
    except Exception as e:
        logging.error(
            f"Błąd podczas oczekiwania na zakończenie drukowania: {str(e)}")
        return False
