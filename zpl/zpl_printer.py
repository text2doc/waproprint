# -*- coding: utf-8 -*-
# zpl_printer.py

"""
Funkcje do drukowania dokumentów w formacie ZPL na drukarkach Zebra
"""

import os
import sys
import time
import tempfile
import subprocess
import logging
from zpl.html_to_zpl import *
from zpl.zpl_converter import HtmlToZpl
from zpl.zpl_utils import get_available_printers, get_default_printer

# Próba importu win32print dla drukowania w systemie Windows
try:
    import win32print

    WINDOWS_PRINTING = True
except ImportError:
    WINDOWS_PRINTING = False


def print_zpl(zpl_data, printer_name=None):
    """
    Wysyła dane ZPL do drukarki

    Args:
        zpl_data (str): Dane ZPL do wydrukowania
        printer_name (str): Nazwa drukarki (domyślnie: drukarki domyślnej)

    Returns:
        bool: True jeśli drukowanie powiodło się, False w przeciwnym wypadku
    """
    # Jeśli nie podano nazwy drukarki, użyj domyślnej
    if not printer_name:
        printer_name = get_default_printer()
        if not printer_name:
            logging.error("Nie znaleziono drukarki domyślnej")
            return False

    try:
        # Sprawdzanie, czy jesteśmy na Windows
        if sys.platform.startswith('win'):
            try:
                # Próba wydruku za pomocą systemu drukowania Windows
                if WINDOWS_PRINTING:
                    # Otwórz drukarkę
                    hPrinter = win32print.OpenPrinter(printer_name)
                    try:
                        # Rozpocznij dokument
                        hJob = win32print.StartDocPrinter(
                            hPrinter, 1, ("ZPL Document", None, "RAW"))
                        try:
                            # Rozpocznij stronę
                            win32print.StartPagePrinter(hPrinter)
                            # Zapisz dane ZPL
                            win32print.WritePrinter(
                                hPrinter, zpl_data.encode('utf-8'))
                            # Zakończ stronę
                            win32print.EndPagePrinter(hPrinter)
                        finally:
                            # Zakończ dokument
                            win32print.EndDocPrinter(hPrinter)
                    finally:
                        # Zamknij drukarkę
                        win32print.ClosePrinter(hPrinter)

                    logging.info(
                        f"Pomyślnie wysłano dane do drukarki {printer_name}")
                    return True
                else:
                    raise ImportError("win32print nie jest dostępny")
            except ImportError:
                logging.warning(
                    "Moduł win32print nie znaleziony, używanie alternatywnej metody drukowania")
            except Exception as e:
                logging.error(
                    f"Błąd podczas korzystania z drukowania Windows: {e}")
                logging.info("Używanie alternatywnej metody drukowania")

            # Alternatywna metoda drukowania (używanie komendy copy dla Windows)
            try:
                # Utworzenie tymczasowego pliku z kodem ZPL
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, suffix='.zpl')
                temp_file_name = temp_file.name

                # Zapisanie kodu ZPL do pliku (w trybie binarnym)
                with open(temp_file_name, 'wb') as f:
                    f.write(zpl_data.encode('utf-8'))

                # Komenda do drukowania w Windows
                print_command = f'copy /b "{temp_file_name}" "{printer_name}"'
                logging.info(f"Wykonuję komendę: {print_command}")
                subprocess.run(print_command, shell=True, check=True)

                logging.info(
                    f"Pomyślnie wysłano dane do drukarki {printer_name}")
                return True
            except Exception as e:
                logging.error(f"Błąd wysyłania danych do drukarki: {e}")
                return False
            finally:
                # Usunięcie tymczasowego pliku
                try:
                    # Krótkie opóźnienie przed usunięciem pliku
                    time.sleep(1)
                    os.unlink(temp_file_name)
                except Exception as e:
                    logging.warning(
                        f"Błąd podczas usuwania pliku tymczasowego: {e}")

        # Na innych systemach (Linux, Mac)
        else:
            try:
                # Utworzenie tymczasowego pliku z kodem ZPL
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, suffix='.zpl')
                temp_file_name = temp_file.name

                # Zapisanie kodu ZPL do pliku
                with open(temp_file_name, 'wb') as f:
                    f.write(zpl_data.encode('utf-8'))

                # Komenda do drukowania w Linux/Mac
                print_command = f'lp -d "{printer_name}" "{temp_file_name}"'
                logging.info(f"Wykonuję komendę: {print_command}")
                subprocess.run(print_command, shell=True, check=True)

                logging.info(
                    f"Pomyślnie wysłano dane do drukarki {printer_name}")
                return True
            except Exception as e:
                logging.error(f"Błąd wysyłania danych do drukarki: {e}")
                return False
            finally:
                # Usunięcie tymczasowego pliku
                try:
                    os.unlink(temp_file_name)
                except Exception as e:
                    logging.warning(
                        f"Błąd podczas usuwania pliku tymczasowego: {e}")

    except Exception as e:
        logging.error(f"Nieoczekiwany błąd podczas drukowania: {e}")
        return False


def save_zpl_to_file(zpl_data, output_file):
    """
    Zapisuje dane ZPL do pliku

    Args:
        zpl_data (str): Dane ZPL do zapisania
        output_file (str): Ścieżka do pliku wyjściowego

    Returns:
        bool: True jeśli zapis powiódł się, False w przeciwnym wypadku
    """
    try:
        # Upewnij się, że katalog wyjściowy istnieje
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Zapisz do pliku
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(zpl_data)

        logging.info(f"Zapisano kod ZPL do pliku {output_file}")
        return True
    except Exception as e:
        logging.error(f"Błąd podczas zapisywania kodu ZPL do pliku: {e}")
        return False


def print_html_from_file(file_path, printer_name=None, dpi=203, label_width=4.0, label_height=6.0,
                         font_size=0, encoding='utf8', save_zpl=True, output_file=None,
                         interactive=False):
    """
    Konwertuje plik HTML do formatu ZPL i drukuje na drukarce Zebra

    Args:
        file_path (str): Ścieżka do pliku HTML
        printer_name (str): Nazwa drukarki (domyślnie: wybór z listy)
        dpi (int): Rozdzielczość drukarki w DPI (domyślnie: 203)
        label_width (float): Szerokość etykiety w calach (domyślnie: 4.0)
        label_height (float): Wysokość etykiety w calach (domyślnie: 6.0, 0 dla auto)
        font_size (int): Podstawowy rozmiar czcionki (domyślnie: 0)
        encoding (str): Kodowanie znaków (domyślnie: cp852)
        save_zpl (bool): Czy zapisać kod ZPL do pliku (domyślnie: False)
        output_file (str): Ścieżka do pliku wyjściowego ZPL (domyślnie: auto)
        interactive (bool): Tryb interaktywny (domyślnie: False)

    Returns:
        bool: True jeśli drukowanie powiodło się, False w przeciwnym wypadku
    """
    try:
        # Sprawdź, czy plik HTML istnieje
        if not os.path.exists(file_path):
            logging.error(f"Plik HTML nie istnieje: {file_path}")
            return False

        # Odczytaj zawartość pliku HTML
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Utwórz konwerter HTML do ZPL
        converter = HtmlToZpl(
            printer_name=printer_name,
            dpi=dpi,
            label_width=label_width,
            label_height=label_height,
            font_size=font_size,
            encoding=encoding,
            interactive=interactive
        )

        # Konwertuj HTML do ZPL
        zpl_data = converter.html_to_zpl(html_content)

        # Zapisz kod ZPL do pliku, jeśli zażądano
        if save_zpl:
            if not output_file:
                # Automatyczna nazwa pliku wyjściowego
                output_file = os.path.splitext(file_path)[0] + ".zpl"

            # Zapisz ZPL do pliku
            save_zpl_to_file(zpl_data, output_file)

        # Drukuj ZPL
        if printer_name:
            result = print_zpl(zpl_data, printer_name)
            if result:
                logging.info(
                    f"Pomyślnie wydrukowano dokument HTML: {file_path}")
            else:
                logging.error(
                    f"Błąd podczas drukowania dokumentu HTML: {file_path}")
            return result
        elif interactive:
            # W trybie interaktywnym zapytaj, czy drukować
            drukarki = get_available_printers()
            if drukarki:
                print("Dostępne drukarki:")
                for i, drukarka in enumerate(drukarki, 1):
                    print(f"{i}. {drukarka}")

                wybor = input(
                    "\nWybierz numer drukarki lub wpisz jej nazwę (Enter, aby pominąć drukowanie): ")

                if wybor:
                    try:
                        indeks = int(wybor) - 1
                        if 0 <= indeks < len(drukarki):
                            printer_name = drukarki[indeks]
                        else:
                            printer_name = wybor
                    except ValueError:
                        printer_name = wybor

                    if printer_name:
                        result = print_zpl(zpl_data, printer_name)
                        if result:
                            logging.info(
                                f"Pomyślnie wydrukowano dokument HTML: {file_path}")
                        else:
                            logging.error(
                                f"Błąd podczas drukowania dokumentu HTML: {file_path}")
                        return result
            else:
                print("Nie znaleziono drukarek. Drukowanie pominięte.")

        # Jeśli nie drukowano, ale zapisano plik ZPL, zwróć True
        if save_zpl:
            return True

        # W przeciwnym razie zwróć False
        logging.warning("Dokument nie został wydrukowany ani zapisany.")
        return False

    except Exception as e:
        logging.error(f"Błąd podczas przetwarzania pliku HTML: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False  # !/usr/bin/env python3
