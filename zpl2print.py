import os
import sys
import time
import logging
import glob
from typing import Dict, Any, Optional, List, Tuple, Set

# Windows-specific imports
try:
    import win32print
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    if sys.platform == 'win32':
        logging.warning(
            "pywin32 is not installed. Windows printing functionality will be disabled.")
    else:
        logging.info(
            "Non-Windows platform detected. Windows printing functionality is not available.")


def print_zpl_file(zpl_file_path: str, printer_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Drukuje plik ZPL na wskazanej drukarce oraz monitoruje status wydruku.
    Na platformach innych niż Windows, funkcja zwraca błąd.

    Parametry:
    - zpl_file_path (str): Ścieżka do pliku ZPL
    - printer_name (str, optional): Nazwa drukarki. Jeśli None, używa domyślnej drukarki ZDesigner GK420d

    Zwraca:
    - dict: Słownik zawierający status wydruku i ewentualny komunikat błędu
        {
            'success': bool,
            'message': str,
            'error': Optional[str],
            'status': str  # 'printed', 'queued' lub 'error'
        }
    """
    if not WIN32_AVAILABLE:
        return {
            'success': False,
            'message': 'Windows printing is not available on this platform',
            'error': 'win32print module not available',
            'status': 'error'
        }

    logger = logging.getLogger(__name__)

    try:
        # Sprawdź, czy plik istnieje
        if not os.path.exists(zpl_file_path):
            logger.error(f"Plik {zpl_file_path} nie istnieje.")
            return {
                'success': False,
                'message': f"Błąd: Plik {zpl_file_path} nie istnieje.",
                'status': 'error'
            }

        # Ustaw domyślną drukarkę, jeśli nie podano
        if printer_name is None:
            printer_name = "ZDesigner GK420d"
            logger.info(f"Używam domyślnej drukarki: {printer_name}")

        # Sprawdź, czy drukarka istnieje w systemie
        printers = get_available_printers()
        printer_names = [printer['name'] for printer in printers]

        if printer_name not in printer_names:
            logger.error(
                f"Drukarka '{printer_name}' nie została znaleziona w systemie.")
            return {
                'success': False,
                'message': f"Błąd: Drukarka '{printer_name}' nie została znaleziona w systemie. "
                f"Dostępne drukarki: {', '.join(printer_names)}",
                'status': 'error'
            }

        # Sprawdź status drukarki przed wydrukiem
        printer_status = get_printer_status(printer_name)
        if not printer_status['ready']:
            logger.warning(
                f"Drukarka {printer_name} nie jest gotowa: {printer_status['status_message']}")
            return {
                'success': False,
                'message': f"Drukarka {printer_name} nie jest gotowa: {printer_status['status_message']}",
                'status': 'error'
            }

        # Wczytaj zawartość pliku ZPL
        with open(zpl_file_path, 'rb') as f:
            zpl_content = f.read()

        # Usuń białe znaki na początku i końcu pliku
        zpl_content = zpl_content.strip()

        # Sprawdź, czy plik ZPL ma poprawną strukturę (zaczyna się od ^XA i kończy ^XZ)
        if not zpl_content.startswith(b'^XA') or not zpl_content.endswith(b'^XZ'):
            logger.warning(
                "Plik ZPL nie ma standardowego początku ^XA lub końca ^XZ. Próba naprawy pliku.")
            # Próba naprawy pliku ZPL
            if not zpl_content.startswith(b'^XA'):
                zpl_content = b'^XA' + zpl_content
            if not zpl_content.endswith(b'^XZ'):
                zpl_content = zpl_content + b'^XZ'

        # Drukowanie bezpośrednio przez RAW - używamy context managera do obsługi zasobów
        logger.info(
            f"Rozpoczynam drukowanie pliku {zpl_file_path} na drukarce {printer_name}...")

        # Funkcja pomocnicza dla czystszego kodu
        result = send_to_printer(printer_name, zpl_content)
        if not result['success']:
            return result

        # Sprawdź status kolejki drukarki po wysłaniu
        time.sleep(1.5)  # Daj trochę czasu na aktualizację statusu

        # Sprawdź, czy są jakieś dokumenty w kolejce
        jobs = get_printer_jobs(printer_name)

        if jobs:
            job_names = [job["pDocument"] for job in jobs]
            logger.warning(
                f"Dokument został wysłany, ale pozostaje w kolejce. Dokumenty w kolejce: {', '.join(job_names)}")

            # Próba alternatywnej metody drukowania - bezpośrednio przez USB/COM
            logger.info("Próbuję alternatywnej metody drukowania...")

            # Najpierw wyczyść kolejkę
            clear_printer_queue(printer_name)

            # Spróbuj wydrukować bezpośrednio przez port
            direct_result = try_alternative_printing(zpl_file_path)
            if direct_result['success']:
                return {
                    'success': True,
                    'message': f"Plik {zpl_file_path} został pomyślnie wydrukowany alternatywną metodą na drukarce {printer_name}.",
                    'status': 'printed'
                }
            else:
                return {
                    'success': False,
                    'message': f"Plik {zpl_file_path} nie został wydrukowany ani standardową, ani alternatywną metodą.",
                    'status': 'error'
                }
        else:
            logger.info(
                f"Plik {zpl_file_path} został pomyślnie wydrukowany na drukarce {printer_name}.")
            return {
                'success': True,
                'message': f"Plik {zpl_file_path} został pomyślnie wydrukowany na drukarce {printer_name}.",
                'status': 'printed'
            }

    except Exception as e:
        logger.exception(
            f"Wystąpił nieoczekiwany błąd podczas drukowania: {str(e)}")
        return {
            'success': False,
            'message': f"Wystąpił błąd podczas drukowania: {str(e)}",
            'status': 'error'
        }


def try_alternative_printing(zpl_file_path: str) -> Dict[str, Any]:
    """
    Próbuje wydrukować plik ZPL za pomocą alternatywnych metod.

    Parametry:
    - zpl_file_path: Ścieżka do pliku ZPL

    Zwraca:
    - Słownik ze statusem operacji
    """
    logger = logging.getLogger(__name__)

    # Lista potencjalnych portów do próby
    ports = ["USB001", "USB002", "USB003", "COM1", "COM3", "COM4"]

    for port in ports:
        try:
            logger.info(f"Próbuję drukować na porcie {port}...")
            result = print_direct_to_port(zpl_file_path, port)
            if result['success']:
                return result
        except Exception as e:
            logger.warning(
                f"Nie udało się drukować na porcie {port}: {str(e)}")

    return {
        'success': False,
        'message': "Nie udało się wydrukować za pomocą żadnej z alternatywnych metod.",
        'status': 'error'
    }


def send_to_printer(printer_name: str, data: bytes) -> Dict[str, Any]:
    """
    Wysyła dane do drukarki.
    Na platformach innych niż Windows, funkcja zwraca błąd.

    Parametry:
    - printer_name: Nazwa drukarki
    - data: Dane do wysłania (w formacie bajtowym)

    Zwraca:
    - Słownik ze statusem operacji
    """
    if not WIN32_AVAILABLE:
        return {
            'success': False,
            'message': 'Windows printing is not available on this platform',
            'error': 'win32print module not available'
        }
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            hJob = win32print.StartDocPrinter(
                hPrinter, 1, ("ZPL Document", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, data)
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)

        return {
            'success': True,
            'message': "Dane zostały wysłane do drukarki.",
            'status': 'sent'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Błąd podczas wysyłania danych do drukarki: {str(e)}",
            'status': 'error'
        }


def get_available_printers() -> List[Dict[str, Any]]:
    """
    Zwraca listę dostępnych drukarek w systemie.
    Na platformach innych niż Windows, zwraca pustą listę.

    Zwraca:
    - Lista słowników zawierających informacje o drukarkach
    """
    if not WIN32_AVAILABLE:
        return []
    printers = []
    for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
        printer_info = {
            'name': p[2],
            'port': p[1],
            'driver': p[3],
            'attributes': p[0]
        }
        printers.append(printer_info)

    return printers


def get_printer_status(printer_name: str) -> Dict[str, Any]:
    """
    Pobiera status drukarki.
    Na platformach innych niż Windows, zwraca status niedostępny.

    Parametry:
    - printer_name: Nazwa drukarki

    Zwraca:
    - Słownik ze statusem drukarki
    """
    if not WIN32_AVAILABLE:
        return {
            'available': False,
            'status': 'unavailable',
            'message': 'Windows printing is not available on this platform'
        }
    result = {
        'ready': True,
        'status': 0,
        'status_message': "Drukarka gotowa"
    }

    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        try:
            printer_info = win32print.GetPrinter(printer_handle, 2)
            status_codes = {
                win32print.PRINTER_STATUS_PAUSED: "Drukarka wstrzymana",
                win32print.PRINTER_STATUS_ERROR: "Błąd drukarki",
                win32print.PRINTER_STATUS_PENDING_DELETION: "Usuwanie w toku",
                win32print.PRINTER_STATUS_PAPER_JAM: "Zacięcie papieru",
                win32print.PRINTER_STATUS_PAPER_OUT: "Brak papieru",
                win32print.PRINTER_STATUS_MANUAL_FEED: "Oczekiwanie na ręczne podanie papieru",
                win32print.PRINTER_STATUS_PAPER_PROBLEM: "Problem z papierem",
                win32print.PRINTER_STATUS_OFFLINE: "Drukarka offline",
                win32print.PRINTER_STATUS_IO_ACTIVE: "Aktywne I/O",
                win32print.PRINTER_STATUS_BUSY: "Drukarka zajęta",
                win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: "Pojemnik wyjściowy pełny",
                win32print.PRINTER_STATUS_NOT_AVAILABLE: "Drukarka niedostępna",
                win32print.PRINTER_STATUS_WAITING: "Oczekiwanie",
                win32print.PRINTER_STATUS_PROCESSING: "Przetwarzanie",
                win32print.PRINTER_STATUS_INITIALIZING: "Inicjalizacja",
                win32print.PRINTER_STATUS_WARMING_UP: "Rozgrzewanie",
                win32print.PRINTER_STATUS_TONER_LOW: "Niski poziom tonera",
                win32print.PRINTER_STATUS_NO_TONER: "Brak tonera",
                win32print.PRINTER_STATUS_PAGE_PUNT: "Pomijanie strony",
                win32print.PRINTER_STATUS_USER_INTERVENTION: "Wymagana interwencja użytkownika",
                win32print.PRINTER_STATUS_OUT_OF_MEMORY: "Brak pamięci",
                win32print.PRINTER_STATUS_DOOR_OPEN: "Drzwiczki otwarte",
                win32print.PRINTER_STATUS_SERVER_UNKNOWN: "Nieznany status serwera",
                win32print.PRINTER_STATUS_POWER_SAVE: "Oszczędzanie energii"
            }

            result['status'] = printer_info['Status']

            if printer_info['Status'] != 0:
                status_messages = []
                for status_code, status_message in status_codes.items():
                    if printer_info['Status'] & status_code:
                        status_messages.append(status_message)

                if status_messages:
                    result['ready'] = False
                    result['status_message'] = ', '.join(status_messages)
        finally:
            win32print.ClosePrinter(printer_handle)
    except Exception as e:
        result['ready'] = False
        result['status_message'] = f"Błąd podczas sprawdzania statusu drukarki: {str(e)}"

    return result


def get_printer_jobs(printer_name: str) -> List[Dict[str, Any]]:
    """
    Pobiera listę zadań drukowania w kolejce drukarki.
    Na platformach innych niż Windows, zwraca pustą listę.

    Parametry:
    - printer_name: Nazwa drukarki

    Zwraca:
    - Lista słowników z informacjami o zadaniach drukowania
    """
    if not WIN32_AVAILABLE:
        return []
    jobs = []
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(hPrinter, 0, 999)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception:
        pass

    return jobs


def clear_printer_queue(printer_name: str) -> Dict[str, Any]:
    """
    Czyści kolejkę drukarki.
    Na platformach innych niż Windows, zwraca błąd.

    Parametry:
    - printer_name: Nazwa drukarki

    Zwraca:
    - Słownik ze statusem operacji
    """
    if not WIN32_AVAILABLE:
        return {
            'success': False,
            'message': 'Windows printing is not available on this platform',
            'error': 'win32print module not available'
        }
    logger = logging.getLogger(__name__)

    try:
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetPrinter(
                handle, 0, None, win32print.PRINTER_CONTROL_PURGE)
            logger.info(
                f"Kolejka drukarki {printer_name} została wyczyszczona.")
            return {
                'success': True,
                'message': f"Kolejka drukarki {printer_name} została wyczyszczona."
            }
        finally:
            win32print.ClosePrinter(handle)
    except Exception as e:
        logger.error(
            f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}"
        }


def print_direct_to_port(zpl_file_path: str, port_name: str = "COM3", baud_rate: int = 9600) -> Dict[str, Any]:
    """
    Drukuje plik ZPL bezpośrednio przez port COM lub USB.
    Na platformach innych niż Windows, zwraca błąd.

    Parametry:
    - zpl_file_path: Ścieżka do pliku ZPL
    - port_name: Nazwa portu COM lub USB
    - baud_rate: Prędkość transmisji (baud rate)

    Zwraca:
    - Słownik ze statusem operacji
    """
    if not WIN32_AVAILABLE:
        return {
            'success': False,
            'message': 'Direct port printing is not available on this platform',
            'error': 'win32print module not available'
        }
    logger = logging.getLogger(__name__)

    try:
        import serial
        if not os.path.exists(zpl_file_path):
            logger.error(f"Plik {zpl_file_path} nie istnieje.")
            return {
                'success': False,
                'message': f"Plik {zpl_file_path} nie istnieje."
            }

        # Wczytaj zawartość pliku ZPL
        with open(zpl_file_path, 'rb') as f:
            zpl_content = f.read()

        # Otwórz port szeregowy i wyślij dane
        ser = serial.Serial(port_name, baud_rate, timeout=5)
        ser.write(zpl_content)
        ser.close()

        logger.info(
            f"Plik {zpl_file_path} został wysłany bezpośrednio do portu {port_name}.")
        return {
            'success': True,
            'message': f"Plik {zpl_file_path} został wysłany bezpośrednio do portu {port_name}."
        }
    except ImportError:
        logger.error("Biblioteka pyserial nie jest zainstalowana.")
        return {
            'success': False,
            'message': "Biblioteka pyserial nie jest zainstalowana. Zainstaluj ją używając pip install pyserial."
        }
    except Exception as e:
        logger.error(
            f"Błąd podczas wysyłania danych do portu {port_name}: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas wysyłania danych do portu {port_name}: {str(e)}"
        }


def check_and_print_pending_orders(printer_name: str) -> Dict[str, Any]:
    """
    Sprawdza, czy istnieją jakieś pliki ZPL, które nie zostały wydrukowane
    i próbuje je wydrukować.
    Na platformach innych niż Windows, zwraca błąd.

    Parametry:
    - printer_name: Nazwa drukarki

    Zwraca:
    - Słownik ze statusem operacji
    """
    if not WIN32_AVAILABLE:
        return {
            'success': False,
            'message': 'Windows printing is not available on this platform',
            'error': 'win32print module not available',
            'pending_orders': []
        }
    logger = logging.getLogger(__name__)

    try:
        logger.info("Sprawdzanie niewydrukowanych zamówień...")

        # Znormalizowana nazwa drukarki jako nazwa folderu
        normalized_printer_name = normalize_filename(printer_name)

        # Ścieżki do folderów z plikami ZPL
        zo_zpl_dir = get_zo_zpl_dir()
        zo_printed_dir = normalized_printer_name

        # Sprawdź, czy folder ZO_PRINTED istnieje, jeśli nie, utwórz go
        if not os.path.exists(zo_printed_dir):
            os.makedirs(zo_printed_dir)
            logger.info(f"Utworzono folder {zo_printed_dir}")

        # Pobierz listę plików ZPL w folderze źródłowym
        zpl_files = glob.glob(os.path.join(zo_zpl_dir, "*.zpl"))

        # Pobierz listę już wydrukowanych plików
        printed_files = set()
        for printed_file in glob.glob(os.path.join(zo_printed_dir, "*.zpl")):
            printed_files.add(os.path.basename(printed_file))

        # Licznik pomyślnie wydrukowanych plików
        success_count = 0
        failed_count = 0

        # Sprawdź, które pliki nie zostały jeszcze wydrukowane
        for zpl_file in zpl_files:
            file_basename = os.path.basename(zpl_file)

            if file_basename not in printed_files:
                logger.info(
                    f"Znaleziono niewydrukowany plik ZPL: {file_basename}")

                # Drukuj plik
                result = print_zpl_file(zpl_file, printer_name)

                if result['success']:
                    success_count += 1

                    # Zapisz plik jako wydrukowany
                    target_path = os.path.join(zo_printed_dir, file_basename)
                    with open(zpl_file, 'rb') as src_file:
                        with open(target_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())

                    logger.info(
                        f"Plik {file_basename} został pomyślnie wydrukowany i zapisany jako wydrukowany.")
                else:
                    failed_count += 1
                    logger.error(
                        f"Nie udało się wydrukować pliku {file_basename}: {result['message']}")

        return {
            'success': True,
            'message': f"Sprawdzanie zakończone. Wydrukowano {success_count} plików, nie udało się wydrukować {failed_count} plików.",
            'success_count': success_count,
            'failed_count': failed_count
        }

    except Exception as e:
        logger.exception(
            f"Wystąpił błąd podczas sprawdzania niewydrukowanych zamówień: {str(e)}")
        return {
            'success': False,
            'message': f"Wystąpił błąd podczas sprawdzania niewydrukowanych zamówień: {str(e)}",
            'success_count': 0,
            'failed_count': 0
        }


# Funkcje pomocnicze, które są używane w kodzie, ale nie są w przedstawionym fragmencie
# Implementacja może wymagać dostosowania do rzeczywistego środowiska

def normalize_filename(name: str) -> str:
    """
    Normalizuje nazwę pliku, usuwając niedozwolone znaki.

    Parametry:
    - name: Nazwa do znormalizowania

    Zwraca:
    - Znormalizowana nazwa
    """
    # Podstawowa implementacja - w rzeczywistości może być bardziej złożona
    import re
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def get_zo_zpl_dir() -> str:
    """
    Zwraca ścieżkę do folderu z plikami ZPL.

    Zwraca:
    - Ścieżka do folderu
    """
    # W rzeczywistości ta funkcja może odczytywać ścieżkę z konfiguracji
    return "ZO_ZPL"
