import win32print
import logging

def get_printer_ip(printer_name):
    """Pobiera adres IP drukarki na podstawie jej nazwy"""
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        if not printer_handle:
            logging.error(f"Nie można otworzyć drukarki: {printer_name}")
            return None

        printer_info = win32print.GetPrinter(printer_handle, 2)
        win32print.ClosePrinter(printer_handle)

        port_name = printer_info['pPortName']

        # Sprawdź, czy port zawiera adres IP
        if port_name.startswith('IP_'):
            ip_address = port_name[3:]
            logging.info(f"Adres IP drukarki {printer_name}: {ip_address}")
            return ip_address
        elif '.' in port_name and any(c.isdigit() for c in port_name):
            # Próba wyodrębnienia adresu IP z nazwy portu
            parts = port_name.split('_')
            for part in parts:
                if '.' in part and all(p.isdigit() or p == '.' for p in part):
                    logging.info(f"Adres IP drukarki {printer_name}: {part}")
                    return part

        logging.warning(f"Nie można określić adresu IP dla drukarki {printer_name}")
        return None
    except Exception as e:
        logging.error(f"Błąd podczas pobierania adresu IP drukarki: {str(e)}")
        return None
