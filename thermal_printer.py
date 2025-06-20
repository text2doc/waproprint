import os
import sys
import time
import logging
import glob
import json
import re
from typing import Dict, Any, Optional, List, Tuple, Set

# Windows-specific imports
try:
    import win32print
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    if sys.platform == 'win32':
        logging.warning("pywin32 is not installed. Windows printing functionality will be disabled.")
    else:
        logging.info("Non-Windows platform detected. Windows printing functionality is not available.")

# thermal_printer.py

class ThermalPrinterManager:
    """
    Klasa do zarządzania drukarkami termicznymi różnych producentów.
    Obsługuje wykrywanie, konfigurację i drukowanie na różnych modelach drukarek.
    """

    # Znane rodziny drukarek termicznych i ich specyficzne ustawienia
    KNOWN_PRINTER_FAMILIES = {
        "zebra": {
            "patterns": ["ZDesigner", "ZTC", "ZD", "ZT", "GK", "GX", "LP"],
            "default_dpi": 203,
            "encoding": "cp850",
            "start_command": "^XA",
            "end_command": "^XZ",
            "ports": ["USB", "COM"]
        },
        "brother": {
            "patterns": ["QL", "TD", "PT", "Brother"],
            "default_dpi": 300,
            "encoding": "cp850",
            "start_command": "",  # Brother może używać innego formatu niż ZPL
            "end_command": "",
            "ports": ["USB"]
        },
        "epson": {
            "patterns": ["TM-", "Epson"],
            "default_dpi": 180,
            "encoding": "cp850",
            "start_command": "",  # Epson używa ESC/POS zamiast ZPL
            "end_command": "",
            "ports": ["USB", "COM", "LPT"]
        },
        "dymo": {
            "patterns": ["DYMO", "LabelWriter"],
            "default_dpi": 300,
            "encoding": "cp1252",
            "start_command": "",  # DYMO używa własnego formatu
            "end_command": "",
            "ports": ["USB"]
        },
        "generic": {
            "patterns": [],
            "default_dpi": 203,
            "encoding": "cp850",
            "start_command": "^XA",  # Zakładamy ZPL jako domyślny
            "end_command": "^XZ",
            "ports": ["USB", "COM", "LPT"]
        }
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Inicjalizuje menedżera drukarek termicznych.

        Parametry:
        - config_file: Opcjonalna ścieżka do pliku konfiguracyjnego z ustawieniami drukarek
        """
        self.logger = logging.getLogger(__name__)
        self.printers_config = {}
        self.detected_printers = {}

        # Wczytaj konfigurację, jeśli podano plik
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.printers_config = json.load(f)
                self.logger.info(f"Wczytano konfigurację drukarek z {config_file}")
            except Exception as e:
                self.logger.error(f"Błąd podczas wczytywania konfiguracji drukarek: {str(e)}")

        # Wykryj dostępne drukarki
        self.detect_thermal_printers()

    def detect_thermal_printers(self) -> Dict[str, Dict[str, Any]]:
        """
        Wykrywa dostępne drukarki termiczne w systemie i określa ich specyfikacje.

        Zwraca:
        - Słownik zawierający informacje o wykrytych drukarkach termicznych
        """
        thermal_printers = {}

        try:
            # Pobierz wszystkie dostępne drukarki w systemie
            all_printers = self.get_available_printers()

            for printer in all_printers:
                printer_name = printer['name']
                # Sprawdź, czy to jest drukarka termiczna na podstawie nazwy
                printer_family = self._detect_printer_family(printer_name)

                if printer_family:
                    # Określ specyfikacje drukarki
                    printer_specs = self._get_printer_specs(printer_name, printer_family)
                    thermal_printers[printer_name] = {
                        'family': printer_family,
                        'port': printer['port'],
                        'driver': printer['driver'],
                        'specs': printer_specs
                    }
                    self.logger.info(f"Wykryto drukarkę termiczną: {printer_name} (rodzina: {printer_family})")

            self.detected_printers = thermal_printers
            return thermal_printers

        except Exception as e:
            self.logger.error(f"Błąd podczas wykrywania drukarek termicznych: {str(e)}")
            return {}

    def _detect_printer_family(self, printer_name: str) -> Optional[str]:
        """
        Określa rodzinę drukarki na podstawie jej nazwy.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - Nazwa rodziny drukarki lub None, jeśli nie rozpoznano
        """
        printer_name_lower = printer_name.lower()

        # Sprawdź najpierw, czy drukarka jest już skonfigurowana
        if printer_name in self.printers_config:
            return self.printers_config[printer_name].get('family', 'generic')

        # Sprawdź na podstawie wzorców nazw
        for family, specs in self.KNOWN_PRINTER_FAMILIES.items():
            for pattern in specs['patterns']:
                if pattern.lower() in printer_name_lower:
                    return family

        # Sprawdź dodatkowe wskazówki, które mogą sugerować, że jest to drukarka termiczna
        thermal_hints = ["thermal", "label", "etykiet", "tag", "receipt", "paragon", "ticket", "bilet"]
        for hint in thermal_hints:
            if hint in printer_name_lower:
                return "generic"  # Prawdopodobnie drukarka termiczna, ale nie znamy dokładnej rodziny

        return None  # Nie rozpoznano jako drukarka termiczna

    def _get_printer_specs(self, printer_name: str, printer_family: str) -> Dict[str, Any]:
        """
        Pobiera specyfikacje dla drukarki na podstawie jej rodziny.

        Parametry:
        - printer_name: Nazwa drukarki
        - printer_family: Rodzina drukarki

        Zwraca:
        - Słownik zawierający specyfikacje drukarki
        """
        # Sprawdź, czy mamy już konfigurację dla tej drukarki
        if printer_name in self.printers_config:
            return self.printers_config[printer_name].get('specs', {})

        # Pobierz domyślne ustawienia dla rodziny drukarek
        family_defaults = self.KNOWN_PRINTER_FAMILIES.get(printer_family, self.KNOWN_PRINTER_FAMILIES['generic'])

        # Próba wykrycia rozdzielczości (DPI) z nazwy drukarki
        dpi = family_defaults['default_dpi']
        dpi_match = re.search(r'(\d{3})dpi', printer_name, re.IGNORECASE)
        if dpi_match:
            dpi = int(dpi_match.group(1))

        return {
            'dpi': dpi,
            'encoding': family_defaults['encoding'],
            'start_command': family_defaults['start_command'],
            'end_command': family_defaults['end_command'],
            'label_width': 104,  # Domyślna szerokość etykiety w mm
            'label_height': 150,  # Domyślna wysokość etykiety w mm
            'font_size': 10  # Domyślny rozmiar czcionki
        }

    def get_available_printers(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę dostępnych drukarek w systemie.

        Zwraca:
        - Lista słowników zawierających informacje o drukarkach
        """
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

    def get_thermal_printers(self) -> Dict[str, Dict[str, Any]]:
        """
        Zwraca słownik dostępnych drukarek termicznych.

        Zwraca:
        - Słownik zawierający informacje o drukarkach termicznych
        """
        # Jeśli jeszcze nie wykryto drukarek, zrób to teraz
        if not self.detected_printers:
            self.detect_thermal_printers()

        return self.detected_printers

    def get_default_thermal_printer(self) -> Optional[str]:
        """
        Zwraca nazwę domyślnej drukarki termicznej.

        Zwraca:
        - Nazwa domyślnej drukarki termicznej lub None, jeśli nie znaleziono
        """
        # Sprawdź, czy mamy skonfigurowaną domyślną drukarkę
        for printer_name, config in self.printers_config.items():
            if config.get('default', False) and printer_name in self.detected_printers:
                return printer_name

        # Jeśli nie, wybierz pierwszą dostępną drukarkę termiczną Zebra
        for printer_name, info in self.detected_printers.items():
            if info['family'] == 'zebra':
                return printer_name

        # Jeśli nie znaleziono drukarki Zebra, wybierz pierwszą dostępną drukarkę termiczną
        if self.detected_printers:
            return list(self.detected_printers.keys())[0]

        return None

    def save_configuration(self, config_file: str) -> bool:
        """
        Zapisuje konfigurację drukarek do pliku.

        Parametry:
        - config_file: Ścieżka do pliku konfiguracyjnego

        Zwraca:
        - True, jeśli zapis się powiódł, False w przeciwnym razie
        """
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.printers_config, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Zapisano konfigurację drukarek do {config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania konfiguracji drukarek: {str(e)}")
            return False

    def set_default_thermal_printer(self, printer_name: str) -> bool:
        """
        Ustawia domyślną drukarkę termiczną.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - True, jeśli operacja się powiodła, False w przeciwnym razie
        """
        if printer_name not in self.detected_printers:
            self.logger.error(f"Drukarka {printer_name} nie jest dostępna w systemie")
            return False

        # Usuń flagę domyślnej drukarki dla wszystkich drukarek
        for name in self.printers_config:
            if 'default' in self.printers_config[name]:
                self.printers_config[name]['default'] = False

        # Ustaw nową domyślną drukarkę
        if printer_name not in self.printers_config:
            self.printers_config[printer_name] = {}

        self.printers_config[printer_name]['default'] = True
        self.printers_config[printer_name]['family'] = self.detected_printers[printer_name]['family']
        self.printers_config[printer_name]['specs'] = self.detected_printers[printer_name]['specs']

        self.logger.info(f"Ustawiono drukarkę {printer_name} jako domyślną drukarkę termiczną")
        return True

    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """
        Pobiera status drukarki.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - Słownik ze statusem drukarki
        """
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

                # Dodatkowe informacje o drukarce
                result['attributes'] = printer_info.get('Attributes', 0)
                result['jobs_count'] = printer_info.get('cJobs', 0)
                result['printer_name'] = printer_info.get('pPrinterName', printer_name)
                result['location'] = printer_info.get('pLocation', '')
                result['port'] = printer_info.get('pPortName', '')

            finally:
                win32print.ClosePrinter(printer_handle)
        except Exception as e:
            result['ready'] = False
            result['status_message'] = f"Błąd podczas sprawdzania statusu drukarki: {str(e)}"

        return result

    def get_printer_jobs(self, printer_name: str) -> List[Dict]:
        """
        Pobiera listę zadań drukowania w kolejce drukarki.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - Lista słowników z informacjami o zadaniach drukowania
        """
        jobs = []
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                jobs = win32print.EnumJobs(hPrinter, 0, 999)
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania zadań drukarki {printer_name}: {str(e)}")

        return jobs

    def clear_printer_queue(self, printer_name: str) -> Dict[str, Any]:
        """
        Czyści kolejkę drukarki.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - Słownik ze statusem operacji
        """
        try:
            handle = win32print.OpenPrinter(printer_name)
            try:
                win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_PURGE)
                self.logger.info(f"Kolejka drukarki {printer_name} została wyczyszczona.")
                return {
                    'success': True,
                    'message': f"Kolejka drukarki {printer_name} została wyczyszczona."
                }
            finally:
                win32print.ClosePrinter(handle)
        except Exception as e:
            self.logger.error(f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}")
            return {
                'success': False,
                'message': f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}"
            }

    def clear_printer_queue2(self, printer_name: str) -> Dict[str, Any]:
        """
        Czyści kolejkę drukarki.

        Parametry:
        - printer_name: Nazwa drukarki

        Zwraca:
        - Słownik ze statusem operacji
        """
        try:
            try:
                import subprocess
                subprocess.run(['rundll32', 'printui.dll,PrintUIEntry', '/k', '/n', printer_name], check=True)
                self.logger.info(f"Kolejka drukarki {printer_name} została wyczyszczona.")
                return {
                    'success': True,
                    'message': f"Kolejka drukarki {printer_name} została wyczyszczona."
                }
            finally:
                pass
        except Exception as e:
            self.logger.error(f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}")
            return {
                'success': False,
                'message': f"Błąd podczas czyszczenia kolejki drukarki {printer_name}: {str(e)}"
            }

    def print_zpl_file(self, zpl_file_path: str, printer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Drukuje plik ZPL na wskazanej drukarce oraz monitoruje status wydruku.

        Parametry:
        - zpl_file_path (str): Ścieżka do pliku ZPL
        - printer_name (str, optional): Nazwa drukarki. Jeśli None, używa domyślnej drukarki termicznej

        Zwraca:
        - dict: Słownik zawierający status wydruku i ewentualny komunikat błędu
        """
        try:
            # Sprawdź, czy plik istnieje
            if not os.path.exists(zpl_file_path):
                self.logger.error(f"Plik {zpl_file_path} nie istnieje.")
                return {
                    'success': False,
                    'message': f"Błąd: Plik {zpl_file_path} nie istnieje.",
                    'status': 'error'
                }

            # Jeśli nie podano drukarki, użyj domyślnej
            if printer_name is None:
                printer_name = self.get_default_thermal_printer()
                if printer_name is None:
                    self.logger.error("Brak dostępnych drukarek termicznych.")
                    return {
                        'success': False,
                        'message': "Błąd: Brak dostępnych drukarek termicznych.",
                        'status': 'error'
                    }
                self.logger.info(f"Używam domyślnej drukarki termicznej: {printer_name}")

            # Sprawdź, czy drukarka istnieje w systemie
            all_printers = self.get_available_printers()
            printer_names = [printer['name'] for printer in all_printers]

            if printer_name not in printer_names:
                self.logger.error(f"Drukarka '{printer_name}' nie została znaleziona w systemie.")
                return {
                    'success': False,
                    'message': f"Błąd: Drukarka '{printer_name}' nie została znaleziona w systemie. "
                               f"Dostępne drukarki: {', '.join(printer_names)}",
                    'status': 'error'
                }

            # Sprawdź status drukarki przed wydrukiem
            printer_status = self.get_printer_status(printer_name)
            if not printer_status['ready']:
                self.logger.warning(f"Drukarka {printer_name} nie jest gotowa: {printer_status['status_message']}")
                return {
                    'success': False,
                    'message': f"Drukarka {printer_name} nie jest gotowa: {printer_status['status_message']}",
                    'status': 'error'
                }

            # Wczytaj i przygotuj zawartość pliku ZPL
            zpl_content = self._prepare_zpl_content(zpl_file_path, printer_name)
            if isinstance(zpl_content, dict) and not zpl_content.get('success', False):
                return zpl_content

            # Drukowanie
            self.logger.info(f"Rozpoczynam drukowanie pliku {zpl_file_path} na drukarce {printer_name}...")

            # Funkcja pomocnicza dla czystszego kodu
            result = self._send_to_printer(printer_name, zpl_content)
            if not result['success']:
                return result

            # Sprawdź status kolejki drukarki po wysłaniu
            time.sleep(1.5)  # Daj trochę czasu na aktualizację statusu

            # Sprawdź, czy są jakieś dokumenty w kolejce
            jobs = self.get_printer_jobs(printer_name)

            if jobs:
                job_names = [job["pDocument"] for job in jobs]
                self.logger.warning(
                    f"Dokument został wysłany, ale pozostaje w kolejce. Dokumenty w kolejce: {', '.join(job_names)}")

                # Próba alternatywnej metody drukowania - bezpośrednio przez USB/COM
                self.logger.info("Próbuję alternatywnej metody drukowania...")

                # Najpierw wyczyść kolejkę
                self.clear_printer_queue2(printer_name)

                # Spróbuj wydrukować bezpośrednio przez port
                #direct_result = self._try_alternative_printing(zpl_file_path, printer_name)
                # if direct_result['success']:
                #     return {
                #         'success': True,
                #         'message': f"Plik {zpl_file_path} został pomyślnie wydrukowany alternatywną metodą na drukarce {printer_name}.",
                #         'status': 'printed'
                #     }
                # else:
                #     return {
                #         'success': False,
                #         'message': f"Plik {zpl_file_path} nie został wydrukowany ani standardową, ani alternatywną metodą.",
                #         'status': 'error'
                #     }
            else:
                self.logger.info(f"Plik {zpl_file_path} został pomyślnie wydrukowany na drukarce {printer_name}.")
                return {
                    'success': True,
                    'message': f"Plik {zpl_file_path} został pomyślnie wydrukowany na drukarce {printer_name}.",
                    'status': 'printed'
                }

        except Exception as e:
            self.logger.exception(f"Wystąpił nieoczekiwany błąd podczas drukowania: {str(e)}")
            return {
                'success': False,
                'message': f"Wystąpił błąd podczas drukowania: {str(e)}",
                'status': 'error'
            }

    def _prepare_zpl_content(self, zpl_file_path: str, printer_name: str) -> bytes:
        """
        Przygotowuje zawartość pliku ZPL do drukowania, dostosowując ją do specyfiki drukarki.

        Parametry:
        - zpl_file_path: Ścieżka do pliku ZPL
        - printer_name: Nazwa drukarki

        Zwraca:
        - Dane bajtowe gotowe do wysłania do drukarki lub słownik z błędem
        """
        try:
            # Wczytaj zawartość pliku ZPL
            with open(zpl_file_path, 'rb') as f:
                zpl_content = f.read()

            # Usuń białe znaki na początku i końcu pliku
            zpl_content = zpl_content.strip()

            # Pobierz rodzinę drukarki i jej specyfikacje
            printer_info = self.detected_printers.get(printer_name, {})
            printer_family = printer_info.get('family', 'generic')
            printer_specs = printer_info.get('specs', {})

            if not printer_specs:
                printer_specs = self.KNOWN_PRINTER_FAMILIES.get('generic', {})

            start_command = printer_specs.get('start_command', '^XA').encode()
            end_command = printer_specs.get('end_command', '^XZ').encode()

            # Tylko dla drukarek Zebra sprawdź i napraw strukturę ZPL
            if printer_family == 'zebra':
                # Sprawdź, czy plik ZPL ma poprawną strukturę (zaczyna się od ^XA i kończy ^XZ)
                if not zpl_content.startswith(b'^XA') or not zpl_content.endswith(b'^XZ'):
                    self.logger.warning(
                        "Plik ZPL nie ma standardowego początku ^XA lub końca ^XZ. Próba naprawy pliku.")
                    # Próba naprawy pliku ZPL
                    if not zpl_content.startswith(b'^XA'):
                        zpl_content = b'^XA' + zpl_content
                    if not zpl_content.endswith(b'^XZ'):
                        zpl_content = zpl_content + b'^XZ'

            # Dla drukarek innych niż Zebra, które nie używają ZPL, konwertuj dane
            elif printer_family != 'zebra' and start_command and end_command:
                # Jeśli plik jest w formacie ZPL, ale drukarka nie obsługuje ZPL, 
                # spróbuj konwertować do odpowiedniego formatu (na razie tylko usuwamy ZPL tags)
                if zpl_content.startswith(b'^XA') and zpl_content.endswith(b'^XZ'):
                    # Usuwamy tagi ZPL i dodajemy właściwe komendy dla danej rodziny drukarek
                    zpl_content = zpl_content.replace(b'^XA', b'').replace(b'^XZ', b'')
                    zpl_content = start_command + zpl_content + end_command

            return zpl_content

        except Exception as e:
            self.logger.error(f"Błąd podczas przygotowywania pliku ZPL: {str(e)}")
            return {
                'success': False,
                'message': f"Błąd podczas przygotowywania pliku ZPL: {str(e)}",
                'status': 'error'
            }

    def _send_to_printer(self, printer_name: str, data: bytes) -> Dict[str, Any]:
        """
        Wysyła dane do drukarki.

        Parametry:
        - printer_name: Nazwa drukarki
        - data: Dane do wysłania (w formacie bajtowym)

        Zwraca:
        - Słownik ze statusem operacji
        """
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("ZPL Document", None, "RAW"))
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


    def _try_alternative_printing(self, zpl_file_path: str, printer_name: str) -> Dict[str, Any]:
        """
        Próbuje wydrukować plik ZPL za pomocą alternatywnych metod.

        Parametry:
        - zpl_file_path: Ścieżka do pliku ZPL
        - printer_name: Nazwa drukarki

        Zwraca:
        - Słownik ze statusem operacji
        """
        # Pobierz informacje o drukarce
        printer_info = self.detected_printers.get(printer_name, {})
        printer_family = printer_info.get('family', 'generic')

        # Pobierz potencjalne porty dla tej rodziny drukarek
        potential_ports = self.KNOWN_PRINTER_FAMILIES.get(printer_family, {}).get('ports', ["USB", "COM"])

        # Lista portów do próby
        ports = []

        # Dodaj porty z nazwą drukarki
        for port_type in potential_ports:
            if port_type == "USB":
                ports.extend([f"USB{i:03d}" for i in range(1, 10)])
            elif port_type == "COM":
                ports.extend([f"COM{i}" for i in range(1, 10)])
            elif port_type == "LPT":
                ports.extend([f"LPT{i}" for i in range(1, 4)])

        # Dodaj port z informacji o drukarce, jeśli istnieje
        if 'port' in printer_info and printer_info['port']:
            ports.insert(0, printer_info['port'])  # Dodaj na początek listy, aby był sprawdzany jako pierwszy

        # Usuń duplikaty
        ports = list(dict.fromkeys(ports))

        self.logger.info(f"Próbuję drukować na portach: {', '.join(ports)}")

        # Próbuj drukować na każdym porcie
        for port in ports:
            try:
                self.logger.info(f"Próbuję drukować na porcie {port}...")
                result = self._print_direct_to_port(zpl_file_path, port, printer_family)
                if result['success']:
                    # Zapisz informację o porcie dla przyszłego użycia
                    if printer_name in self.printers_config:
                        self.printers_config[printer_name]['port'] = port
                    else:
                        self.printers_config[printer_name] = {'port': port}

                    return result
            except Exception as e:
                self.logger.warning(f"Nie udało się drukować na porcie {port}: {str(e)}")

        return {
            'success': False,
            'message': "Nie udało się wydrukować za pomocą żadnej z alternatywnych metod.",
            'status': 'error'
        }


    def _print_direct_to_port(self, zpl_file_path: str, port_name: str, printer_family: str = 'generic',
                              baud_rate: int = 9600) -> Dict[str, Any]:
        """
        Drukuje plik ZPL bezpośrednio przez port COM lub USB.

        Parametry:
        - zpl_file_path: Ścieżka do pliku ZPL
        - port_name: Nazwa portu COM lub USB
        - printer_family: Rodzina drukarki (wpływa na sposób formatowania danych)
        - baud_rate: Prędkość transmisji (baud rate)

        Zwraca:
        - Słownik ze statusem operacji
        """
        try:
            import serial
            if not os.path.exists(zpl_file_path):
                self.logger.error(f"Plik {zpl_file_path} nie istnieje.")
                return {
                    'success': False,
                    'message': f"Plik {zpl_file_path} nie istnieje."
                }

            # Wczytaj zawartość pliku ZPL
            with open(zpl_file_path, 'rb') as f:
                data = f.read()

            # Dostosuj dane do rodziny drukarki
            if printer_family != 'zebra':
                # Pobierz specyfikacje dla rodziny drukarek
                family_specs = self.KNOWN_PRINTER_FAMILIES.get(printer_family, self.KNOWN_PRINTER_FAMILIES['generic'])
                start_command = family_specs.get('start_command', '').encode()
                end_command = family_specs.get('end_command', '').encode()

                # Jeśli dane są w formacie ZPL, a drukarka nie jest Zebra, usuń tagi ZPL
                if data.startswith(b'^XA') and data.endswith(b'^XZ'):
                    data = data.replace(b'^XA', b'').replace(b'^XZ', b'')

                # Dodaj odpowiednie komendy początkowe i końcowe dla danej rodziny drukarek
                if start_command:
                    data = start_command + data
                if end_command:
                    data = data + end_command

            # Otwórz port szeregowy i wyślij dane
            # Ustalamy odpowiednie parametry dla portu
            params = {
                'port': port_name,
                'baudrate': baud_rate,
                'timeout': 5
            }

            # Dodaj parametry specyficzne dla różnych typów portów
            if port_name.startswith('COM'):
                params.update({
                    'bytesize': serial.EIGHTBITS,
                    'parity': serial.PARITY_NONE,
                    'stopbits': serial.STOPBITS_ONE,
                    'xonxoff': False,
                    'rtscts': False,
                    'dsrdtr': False
                })

            # Dla portów USB często wymagane są inne parametry
            elif port_name.startswith('USB'):
                # Niektóre drukarki USB emulują port szeregowy
                if printer_family == 'zebra':
                    params.update({
                        'baudrate': 115200,  # Zebra często używa wyższej prędkości
                        'bytesize': serial.EIGHTBITS,
                        'parity': serial.PARITY_NONE,
                        'stopbits': serial.STOPBITS_ONE
                    })

            # Otwórz port i wyślij dane
            ser = serial.Serial(**params)
            ser.write(data)
            ser.close()

            self.logger.info(f"Plik {zpl_file_path} został wysłany bezpośrednio do portu {port_name}.")
            return {
                'success': True,
                'message': f"Plik {zpl_file_path} został wysłany bezpośrednio do portu {port_name}."
            }
        except ImportError:
            self.logger.error("Biblioteka pyserial nie jest zainstalowana.")
            return {
                'success': False,
                'message': "Biblioteka pyserial nie jest zainstalowana. Zainstaluj ją używając pip install pyserial."
            }
        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania danych do portu {port_name}: {str(e)}")
            return {
                'success': False,
                'message': f"Błąd podczas wysyłania danych do portu {port_name}: {str(e)}"
            }


    def format_zpl_for_printer(self, zpl_content: str, printer_name: Optional[str] = None) -> str:
        """
        Formatuje treść ZPL dla konkretnej drukarki, dodając odpowiednie komendy.

        Parametry:
        - zpl_content: Treść ZPL do sformatowania
        - printer_name: Nazwa drukarki (jeśli None, używa domyślnej)

        Zwraca:
        - Sformatowana treść ZPL
        """
        if printer_name is None:
            printer_name = self.get_default_thermal_printer()
            if not printer_name:
                return zpl_content

        # Pobierz rodzinę drukarki
        printer_info = self.detected_printers.get(printer_name, {})
        printer_family = printer_info.get('family', 'zebra')

        # Dla drukarek Zebra
        if printer_family == 'zebra':
            # Sprawdź, czy zaczyna się od ^XA i kończy ^XZ
            if not zpl_content.startswith('^XA'):
                zpl_content = '^XA' + zpl_content
            if not zpl_content.endswith('^XZ'):
                zpl_content = zpl_content + '^XZ'

            # Dodaj ewentualne specyficzne komendy dla drukarki Zebra
            # np. ustawienia DPI, rozmiar etykiety itp.
            printer_specs = printer_info.get('specs', {})
            dpi = printer_specs.get('dpi', 203)

            # Przykład: Ustaw intensywność druku na podstawie DPI
            if dpi >= 300:
                if not '^PW' in zpl_content:
                    zpl_content = zpl_content.replace('^XA', '^XA^PR2~SD15')

        # Dla innych rodzin drukarek trzeba by zaimplementować odpowiednią konwersję
        # Na razie zwracamy oryginalną treść
        return zpl_content


    def check_and_print_pending_orders(self, printer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Sprawdza, czy istnieją jakieś pliki ZPL, które nie zostały wydrukowane
        i próbuje je wydrukować.

        Parametry:
        - printer_name: Nazwa drukarki (jeśli None, używa domyślnej)

        Zwraca:
        - Słownik ze statusem operacji
        """
        if printer_name is None:
            printer_name = self.get_default_thermal_printer()
            if not printer_name:
                return {
                    'success': False,
                    'message': "Brak dostępnej drukarki termicznej.",
                    'success_count': 0,
                    'failed_count': 0
                }

        try:
            self.logger.info("Sprawdzanie niewydrukowanych zamówień...")

            # Znormalizowana nazwa drukarki jako nazwa folderu
            normalized_printer_name = self._normalize_filename(printer_name)

            # Ścieżki do folderów z plikami ZPL
            zo_zpl_dir = self._get_zo_zpl_dir()
            zo_printed_dir = normalized_printer_name

            # Sprawdź, czy folder ZO_PRINTED istnieje, jeśli nie, utwórz go
            if not os.path.exists(zo_printed_dir):
                os.makedirs(zo_printed_dir)
                self.logger.info(f"Utworzono folder {zo_printed_dir}")

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
                    self.logger.info(f"Znaleziono niewydrukowany plik ZPL: {file_basename}")

                    # Drukuj plik
                    result = self.print_zpl_file(zpl_file, printer_name)

                    if result['success']:
                        success_count += 1

                        # Zapisz plik jako wydrukowany
                        target_path = os.path.join(zo_printed_dir, file_basename)
                        with open(zpl_file, 'rb') as src_file:
                            with open(target_path, 'wb') as dest_file:
                                dest_file.write(src_file.read())

                        self.logger.info(f"Plik {file_basename} został pomyślnie wydrukowany i zapisany jako wydrukowany.")
                    else:
                        failed_count += 1
                        self.logger.error(f"Nie udało się wydrukować pliku {file_basename}: {result['message']}")

            return {
                'success': True,
                'message': f"Sprawdzanie zakończone. Wydrukowano {success_count} plików, nie udało się wydrukować {failed_count} plików.",
                'success_count': success_count,
                'failed_count': failed_count
            }

        except Exception as e:
            self.logger.exception(f"Wystąpił błąd podczas sprawdzania niewydrukowanych zamówień: {str(e)}")
            return {
                'success': False,
                'message': f"Wystąpił błąd podczas sprawdzania niewydrukowanych zamówień: {str(e)}",
                'success_count': 0,
                'failed_count': 0
            }


    def _normalize_filename(self, name: str) -> str:
        """
        Normalizuje nazwę pliku, usuwając niedozwolone znaki.

        Parametry:
        - name: Nazwa do znormalizowania

        Zwraca:
        - Znormalizowana nazwa
        """
        # Podstawowa implementacja - usuwamy znaki niedozwolone w nazwach plików
        import re
        return re.sub(r'[\\/*?:"<>|]', "_", name)


    def _get_zo_zpl_dir(self) -> str:
        """
        Zwraca ścieżkę do folderu z plikami ZPL.

        Zwraca:
        - Ścieżka do folderu
        """
        # W rzeczywistości ta funkcja może odczytywać ścieżkę z konfiguracji
        # Na potrzeby tej implementacji zwracamy domyślną wartość
        return "ZO_ZPL"