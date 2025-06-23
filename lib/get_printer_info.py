import win32print
import logging


def get_printer_info(printer_name):
    """Pobiera szczegółowe informacje o drukarce"""
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        if not printer_handle:
            logging.error(f"Nie można otworzyć drukarki: {printer_name}")
            return None

        printer_info = win32print.GetPrinter(printer_handle, 2)
        win32print.ClosePrinter(printer_handle)

        info = {
            'name': printer_info['pPrinterName'],
            'port': printer_info['pPortName'],
            'driver': printer_info['pDriverName'],
            'description': printer_info['pComment'],
            'location': printer_info['pLocation'],
            'separator_file': printer_info['pSepFile'],
            'print_processor': printer_info['pPrintProcessor'],
            'data_type': printer_info['pDatatype'],
            'parameters': printer_info['pParameters'],
            'attributes': printer_info['Attributes'],
            'priority': printer_info['Priority'],
            'default_priority': printer_info['DefaultPriority'],
            'start_time': printer_info['StartTime'],
            'until_time': printer_info['UntilTime'],
            'status': printer_info['Status'],
            'jobs': printer_info['cJobs'],
            'average_ppm': printer_info['AveragePPM']
        }

        logging.info(f"Pobrano informacje o drukarce {printer_name}")
        return info
    except Exception as e:
        logging.error(
            f"Błąd podczas pobierania informacji o drukarce: {str(e)}")
        return None
