import win32print
import logging

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
                logging.info(f"Zadanie w kolejce: ID={job['JobId']}, Status={job['Status']}, Dokument={job['pDocument']}")
        else:
            logging.info("Kolejka drukarki jest pusta")

        # Zamknij uchwyt do drukarki
        win32print.ClosePrinter(printer_handle)
        return True
    except Exception as e:
        logging.error(f"Błąd podczas sprawdzania kolejki drukarki: {str(e)}")
        return False
