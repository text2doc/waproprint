import socket
import logging

def test_printer_connection(printer_ip, port=9100, timeout=5):
    """Testuje połączenie z drukarką poprzez sprawdzenie dostępności portu"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((printer_ip, port))
        sock.close()

        if result == 0:
            logging.info(f"Połączenie z drukarką {printer_ip}:{port} działa poprawnie")
            return True
        else:
            logging.warning(f"Nie można połączyć się z drukarką {printer_ip}:{port}")
            return False
    except Exception as e:
        logging.error(f"Błąd podczas testowania połączenia z drukarką: {str(e)}")
        return False
