#!/usr/bin/env python
# -*- coding: utf-8 -*-
# lib/Printer.py

import os
import logging
import subprocess
import time
import win32print
from thermal_printer import ThermalPrinterManager


class Printer:
    """
    Klasa obsługująca drukowanie dokumentów na skonfigurowanej drukarce.
    Wspiera drukowanie PDF na drukarkach termicznych bezpośrednio lub przez konwersję do ZPL.
    """

    def __init__(self, printer_name=None):
        """
        Inicjalizuje obiekt drukarki.

        Parametry:
        - printer_name: Nazwa drukarki. Jeśli None, zostanie użyta domyślna drukarka.
        """
        self.logger = logging.getLogger(__name__)
        self.printer_name = printer_name
        self.printer_manager = ThermalPrinterManager()
        self.initialize()

    def initialize(self):
        """Inicjalizuje drukarkę i sprawdza jej dostępność."""
        try:
            if not self.printer_name:
                # Próba użycia domyślnej drukarki termicznej
                self.printer_name = self.printer_manager.get_default_thermal_printer()
                if not self.printer_name:
                    # Jeśli nie znaleziono drukarki termicznej, użyj domyślnej drukarki systemowej
                    self.printer_name = win32print.GetDefaultPrinter()
                    self.logger.info(f"Używam domyślnej drukarki systemowej: {self.printer_name}")
                else:
                    self.logger.info(f"Używam domyślnej drukarki termicznej: {self.printer_name}")

            # Sprawdź, czy drukarka istnieje w systemie
            all_printers = self.printer_manager.get_available_printers()
            printer_names = [printer['name'] for printer in all_printers]

            if self.printer_name not in printer_names:
                self.logger.error(f"Drukarka '{self.printer_name}' nie istnieje w systemie.")
                self.printer_name = None
                return False

            # Sprawdź status drukarki
            printer_status = self.printer_manager.get_printer_status(self.printer_name)
            if not printer_status['ready']:
                self.logger.warning(f"Drukarka {self.printer_name} nie jest gotowa: {printer_status['status_message']}")
                return False

            self.logger.info(f"Drukarka {self.printer_name} jest gotowa do użycia.")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas inicjalizacji drukarki: {str(e)}")
            return False

    def print_pdf(self, pdf_path):
        """
        Drukuje plik PDF na skonfigurowanej drukarce.
        Najpierw próbuje drukować bezpośrednio, a jeśli to się nie powiedzie,
        używa konwersji do ZPL (dla drukarek termicznych).

        Parametry:
        - pdf_path: Ścieżka do pliku PDF do wydrukowania

        Zwraca:
        - True jeśli drukowanie się powiodło, False w przeciwnym razie
        """
        if not self.printer_name:
            self.logger.error("Brak skonfigurowanej drukarki.")
            return False

        if not os.path.exists(pdf_path):
            self.logger.error(f"Plik {pdf_path} nie istnieje.")
            return False

        self.logger.info(f"Próba drukowania pliku {pdf_path} na drukarce {self.printer_name}")

        # Najpierw próbuj bezpośredniego drukowania
        direct_print_result = self._print_pdf_directly(pdf_path)

        if direct_print_result['success']:
            self.logger.info(f"Pomyślnie wydrukowano plik {pdf_path} bezpośrednio.")
            return True

        # Jeśli bezpośrednie drukowanie nie powiodło się, a drukarka jest termiczna,
        # spróbuj konwersji do ZPL
        if self.printer_name in self.printer_manager.get_thermal_printers():
            self.logger.info("Bezpośrednie drukowanie się nie powiodło. Próbuję konwersji do ZPL...")
            zpl_print_result = self._print_pdf_as_zpl(pdf_path)

            if zpl_print_result['success']:
                self.logger.info(f"Pomyślnie wydrukowano plik {pdf_path} poprzez konwersję do ZPL.")
                return True

        # Spróbuj drukować przez zewnętrzny program (Adobe Reader)
        self.logger.info("Wszystkie metody wewnętrzne zawiodły. Próbuję drukować przez zewnętrzną aplikację...")
        if self._print_with_adobe(pdf_path):
            self.logger.info(f"Pomyślnie wydrukowano plik {pdf_path} przy użyciu Adobe Reader.")
            return True

        self.logger.error(f"Nie udało się wydrukować pliku {pdf_path} żadną metodą.")
        return False

    def _print_pdf_directly(self, pdf_path):
        """
        Drukuje plik PDF bezpośrednio na drukarce bez konwersji.

        Parametry:
        - pdf_path: Ścieżka do pliku PDF

        Zwraca:
        - Słownik z informacją o statusie operacji
        """
        try:
            # Metoda 1: Użycie systemowego mechanizmu drukowania przez rundll32
            try:
                self.logger.info(f"Próba drukowania przez rundll32...")
                subprocess.run(
                    ['rundll32.exe', 'mshtml.dll,PrintHTML', pdf_path, '/p:' + self.printer_name],
                    check=True,
                    capture_output=True,
                    timeout=60  # Timeout po 60 sekundach
                )

                self.logger.info(f"Komenda drukowania wykonana pomyślnie")
                direct_print_success = True

            except subprocess.SubprocessError as e:
                self.logger.warning(f"Nie udało się wydrukować PDF przez rundll32: {str(e)}")
                direct_print_success = False

            # Metoda 2: Alternatywna metoda - użycie GhostScript
            if not direct_print_success:
                self.logger.info("Próba drukowania przez GhostScript...")
                try:
                    # Ścieżka do GhostScript może wymagać dostosowania
                    gs_cmd = "gswin64c.exe"  # lub "gswin32c.exe" dla 32-bit

                    args = [
                        gs_cmd, "-dNOPAUSE", "-dBATCH", "-dPrinted", "-dNOSAFER",
                        f"-sDEVICE=mswinpr2",
                        f"-sOutputFile=%printer%{self.printer_name}",
                        pdf_path
                    ]

                    subprocess.run(args, check=True, capture_output=True, timeout=60)
                    self.logger.info(f"PDF został pomyślnie wydrukowany używając GhostScript")
                    direct_print_success = True

                except (subprocess.SubprocessError, FileNotFoundError) as e:
                    self.logger.warning(f"Nie udało się wydrukować PDF przez GhostScript: {str(e)}")
                    direct_print_success = False

            # Sprawdź, czy drukowanie się powiodło
            if direct_print_success:
                # Sprawdź, czy w kolejce są zadania drukowania
                time.sleep(1.5)  # Daj trochę czasu na aktualizację statusu
                jobs = self.printer_manager.get_printer_jobs(self.printer_name)

                if jobs:
                    self.logger.info(f"Dokument został wysłany do drukarki i znajduje się w kolejce")
                    return {
                        'success': True,
                        'message': f"Plik {pdf_path} został wysłany do drukowania i znajduje się w kolejce.",
                        'status': 'queued'
                    }
                else:
                    self.logger.info(f"Dokument został pomyślnie wydrukowany")
                    return {
                        'success': True,
                        'message': f"Plik {pdf_path} został pomyślnie wydrukowany.",
                        'status': 'printed'
                    }
            else:
                # Jeśli obie metody zawiodły, zwróć błąd
                self.logger.error("Nie udało się wydrukować PDF bezpośrednio")
                return {
                    'success': False,
                    'message': f"Nie udało się wydrukować pliku {pdf_path} bezpośrednio.",
                    'status': 'error'
                }

        except Exception as e:
            self.logger.exception(f"Wystąpił nieoczekiwany błąd podczas drukowania PDF: {str(e)}")
            return {
                'success': False,
                'message': f"Wystąpił błąd podczas drukowania PDF: {str(e)}",
                'status': 'error'
            }

    def _print_pdf_as_zpl(self, pdf_path):
        """
        Konwertuje plik PDF do formatu ZPL i drukuje na drukarce termicznej.

        Parametry:
        - pdf_path: Ścieżka do pliku PDF

        Zwraca:
        - Słownik z informacją o statusie operacji
        """
        try:
            from zebrafy import ZebrafyPDF

            # Pobierz informacje o drukarce
            printer_info = self.printer_manager.detected_printers.get(self.printer_name, {})
            printer_specs = printer_info.get('specs', {})
            dpi = printer_specs.get('dpi', 203)

            # Konwertuj PDF do ZPL
            self.logger.info(f"Konwertuję PDF na format ZPL z rozdzielczością {dpi} DPI...")
            with open(pdf_path, "rb") as pdf:
                zpl_string = ZebrafyPDF(
                    pdf.read(),
                    format="ASCII",
                    invert=True,
                    dither=False,
                    threshold=128,
                    dpi=dpi,
                    pos_x=0,
                    pos_y=0,
                    rotation=0,
                    complete_zpl=True,
                    split_pages=False,
                ).to_zpl()

            # Tymczasowo zapisz ZPL do pliku
            temp_zpl_path = f"{os.path.splitext(pdf_path)[0]}.zpl"
            with open(temp_zpl_path, "w") as zpl_file:
                zpl_file.write(zpl_string)

            self.logger.info(f"Zapisano tymczasowy plik ZPL: {temp_zpl_path}")

            # Wydrukuj ZPL na drukarce termicznej
            self.logger.info(f"Drukuję ZPL na drukarce: {self.printer_name}")
            result = self.printer_manager.print_zpl_file(temp_zpl_path, self.printer_name)

            # Opcjonalnie - usuń tymczasowy plik ZPL po wydrukowaniu
            try:
                os.remove(temp_zpl_path)
                self.logger.info(f"Usunięto tymczasowy plik ZPL: {temp_zpl_path}")
            except Exception as e:
                self.logger.warning(f"Nie udało się usunąć tymczasowego pliku ZPL: {str(e)}")

            return result

        except ImportError:
            self.logger.error("Biblioteka zebrafy nie jest zainstalowana. Nie można konwertować do ZPL.")
            return {
                'success': False,
                'message': "Biblioteka zebrafy nie jest zainstalowana. Nie można konwertować do ZPL.",
                'status': 'error'
            }
        except Exception as e:
            self.logger.exception(f"Wystąpił błąd podczas konwersji PDF do ZPL: {str(e)}")
            return {
                'success': False,
                'message': f"Wystąpił błąd podczas konwersji PDF do ZPL: {str(e)}",
                'status': 'error'
            }

    def _print_with_adobe(self, pdf_path):
        """
        Drukuje plik PDF używając Adobe Reader, jeśli jest zainstalowany.

        Parametry:
        - pdf_path: Ścieżka do pliku PDF

        Zwraca:
        - True jeśli drukowanie się powiodło, False w przeciwnym razie
        """
        try:
            # Ścieżki do Adobe Reader
            adobe_paths = [
                r"C:\Program Files (x86)\Adobe\Reader 11.0\Reader\AcroRd32.exe",
                r"C:\Program Files\Adobe\Reader\AcroRd32.exe",
                r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
                r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"
            ]

            adobe_path = None
            for path in adobe_paths:
                if os.path.exists(path):
                    adobe_path = path
                    break

            if not adobe_path:
                self.logger.error("Nie znaleziono zainstalowanego Adobe Reader.")
                return False

            self.logger.info(f"Drukowanie przez Adobe Reader: {adobe_path}")

            # Uruchom Adobe Reader z parametrami do drukowania
            cmd = [adobe_path, "/t", pdf_path, self.printer_name]
            process = subprocess.Popen(cmd, shell=True)

            # Poczekaj na zakończenie procesu z timeout
            try:
                process.wait(timeout=30)
                self.logger.info(f"Adobe Reader zakończył drukowanie z kodem: {process.returncode}")
                return process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.warning("Timeout podczas drukowania przez Adobe Reader.")
                return False

        except Exception as e:
            self.logger.error(f"Błąd podczas drukowania przez Adobe Reader: {str(e)}")
            return False

