#!/usr/bin/env python
# -*- coding: utf-8 -*-
# sql2html.py

"""
Moduł integrujący ulepszoną obsługę drukarek termicznych z istniejącym systemem.
Zintegrowany z funkcjonalnością drukowania plików ZPL na drukarkach sieciowych.
"""

from zpl2print import *
from html2pdf3 import *
import asyncio
import os
import time
import signal
import sys

from thermal_printer import *
from lib.DatabaseManager import DatabaseManager
from lib.ConfigManager import ConfigManager
# from lib.order_processor import  process_todays_orders
from lib.order_processor2 import  process_todays_orders, get_id_uzytkownika_by_order
from lib.file_utils import get_printed_orders, save_order_html, normalize_filename, get_path_order
from lib.file_utils import get_zo_html_dir, get_zo_json_dir, get_zo_zpl_dir, get_zo_pdf_dir
from lib.logger import logger
from zpl.html2zpl import *
from zebrafy import ZebrafyPDF


# Import nowego modułu do obsługi drukowania ZPL
from zpl.zpl_printer import print_zpl_to_network_printer, list_zpl_files


# Obsługa przerwania skryptu
def signal_handler(sig, frame):
    logger.info("Otrzymano sygnał przerwania. Kończenie pracy skryptu...")
    sys.exit(0)


# Rejestracja handlera dla SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

# Pobierz ścieżkę do katalogu skryptu
script_dir = os.path.dirname(os.path.abspath(__file__))


def save_order_zpl(order_number, html_path):
    """Zapisuje plik ZPL dla zamówienia w folderze skonfigurowanym w config.ini"""
    try:
        # Pobierz ścieżkę do katalogu ZPL z konfiguracji
        config = ConfigManager()
        zpl_dir = config.get_zo_zpl_dir()
        if not zpl_dir:
            logger.error("Nie udało się pobrać ścieżki katalogu ZPL z konfiguracji")
            return False

        # Utwórz folder ZPL jeśli nie istnieje
        os.makedirs(zpl_dir, exist_ok=True)

        # Normalizuj nazwę pliku
        normalized_name = normalize_filename(order_number)
        zpl_filename = f"{normalized_name}.zpl"
        zpl_path = os.path.join(zpl_dir, zpl_filename)

        # Pobierz parametry drukarki z konfiguracji
        printer_name = config.get_thermal_printer_name()
        dpi = config.get_printer_dpi()
        label_width = config.get_printer_label_width()
        label_height = config.get_printer_label_height()
        font_size = config.get_printer_font_size()
        encoding = config.get_printer_encoding()

        if not printer_name:
            logger.error("Nie udało się pobrać nazwy drukarki termicznej z konfiguracji")
            return False

        # Konwertuj HTML na ZPL i zapisz do pliku
        result = print_html_from_file(
            file_path=html_path,
            output_file=zpl_path,
            printer_name=printer_name,
            dpi=dpi,
            label_width=label_width,
            label_height=label_height,
            font_size=font_size,
            encoding=encoding,
            save_zpl=True
        )

        if result:
            logger.info(f"Zapisano plik ZPL dla zamówienia {order_number} w {zpl_path}")
            return True
        else:
            logger.error(f"Nie udało się wygenerować pliku ZPL dla zamówienia {order_number}")
            return False

    except Exception as e:
        logger.error(f"Błąd podczas zapisywania pliku ZPL dla zamówienia {order_number}: {str(e)}", exc_info=True)
        return False



def initialize_thermal_printer_manager(config: ConfigManager) -> ThermalPrinterManager:
    """
    Inicjalizuje i konfiguruje menedżera drukarek termicznych.

    Parametry:
    - config: Obiekt ConfigManager z konfiguracją

    Zwraca:
    - Skonfigurowany obiekt ThermalPrinterManager
    """
    try:
        # Ścieżka do pliku konfiguracyjnego drukarek (opcjonalnie)
        printer_config_file = 'thermal_printers.json'

        # Inicjalizacja menedżera drukarek
        printer_manager = ThermalPrinterManager(config_file=printer_config_file)

        # Wykryj dostępne drukarki termiczne
        thermal_printers = printer_manager.get_thermal_printers()
        logger.info(f"Wykryto {len(thermal_printers)} drukarek termicznych")

        # Pobierz nazwę drukarki z konfiguracji
        configured_printer = config.get_thermal_printer_name()

        # Sprawdź, czy drukarka z konfiguracji jest dostępna
        if configured_printer and configured_printer in thermal_printers:
            # Ustaw jako domyślną
            printer_manager.set_default_thermal_printer(configured_printer)
            logger.info(f"Używam drukarki z konfiguracji: {configured_printer}")
        else:
            # Jeśli drukarki z konfiguracji nie znaleziono, użyj pierwszej dostępnej
            default_printer = printer_manager.get_default_thermal_printer()
            if default_printer:
                logger.info(f"Drukarka z konfiguracji nie jest dostępna. Używam drukarki: {default_printer}")
            else:
                logger.warning("Nie znaleziono żadnej drukarki termicznej!")

        # Zapisz konfigurację drukarek do pliku
        printer_manager.save_configuration(printer_config_file)

        return printer_manager
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji menedżera drukarek: {str(e)}")
        return None


# Nowa funkcja drukowania ZPL za pomocą połączenia sieciowego
def print_zpl_network(zpl_path, config=None):
    """
    Drukuje plik ZPL na drukarce sieciowej korzystając z konfiguracji w config.ini.

    Parametry:
    - zpl_path: Ścieżka do pliku ZPL
    - config: Opcjonalny obiekt ConfigManager. Jeśli None, tworzy nowy.

    Zwraca:
    - Słownik z informacją o statusie operacji
    """
    try:
        # Sprawdź, czy plik ZPL istnieje
        if not os.path.exists(zpl_path):
            error_msg = f"Plik ZPL {zpl_path} nie istnieje"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg, 'status': 'error'}

        # Inicjalizacja konfiguracji, jeśli nie została podana
        if config is None:
            config = ConfigManager()
            config.load_config()

        # Pobierz parametry drukarki z konfiguracji
        printer_ip = config.get_thermal_printer_ip()
        port = config.get_thermal_printer_port()

        if not printer_ip:
            logger.error("Nie znaleziono adresu IP drukarki w konfiguracji")
            return {
                'success': False,
                'message': "Nie znaleziono adresu IP drukarki w konfiguracji",
                'status': 'error'
            }

        # Drukowanie ZPL na drukarce sieciowej
        logger.info(f"Drukuję plik ZPL {zpl_path} na drukarce sieciowej {printer_ip}:{port}")
        result = print_zpl_to_network_printer(zpl_path, printer_ip, port, config)

        return result

    except Exception as e:
        logger.exception(f"Wystąpił błąd podczas drukowania ZPL na drukarce sieciowej: {str(e)}")
        return {
            'success': False,
            'message': f"Wystąpił błąd podczas drukowania ZPL: {str(e)}",
            'status': 'error'
        }



from html2pdfs.utils import (
    find_wkhtmltopdf_path,
    generate_temp_filename,
    ensure_directory_exists,
    pdf_to_final_location
)
from html2pdfs.html_processor import preprocess_html, calculate_optimal_height
from html2pdfs.pdf_trimmer import (
    trim_pdf_to_content,
    detect_content_height_from_pdf,
    trim_existing_pdf
)


# Utwórz zmodyfikowaną asynchroniczną funkcję pomocniczą
async def generate_pdf(html_path, pdf_path, label_width_mm, continuous=True, margins=None):
    """
    Generuje plik PDF na podstawie pliku HTML.
    Najpierw generuje PDF za pomocą html_to_pdf, a następnie obcina go za pomocą trim_existing_pdf.

    Parametry:
    - html_path: Ścieżka do pliku HTML
    - pdf_path: Ścieżka docelowa dla pliku PDF
    - label_width_mm: Szerokość etykiety w milimetrach
    - continuous: Czy używać trybu ciągłego bez podziału na strony
    - margins: Marginesy (słownik z kluczami 'top', 'right', 'bottom', 'left')

    Zwraca:
    - Ścieżka do wygenerowanego pliku PDF lub None w przypadku błędu
    """
    try:
        # Najpierw generuj PDF używając html_to_pdf
        logger.info(f"Generowanie wstępnego PDF za pomocą html_to_pdf dla pliku {html_path}")

        initial_pdf = await html_to_pdf(
            url=html_path,
            output_path=pdf_path,
            label_width_mm=label_width_mm,
            continuous=continuous,
            margins=margins or {"top": 0, "right": 0, "bottom": 0, "left": 0},
            css_styles="body { font-size: 12px; line-height: 1.2; } img { max-width: 100%; }"
        )

        if not initial_pdf:
            logger.error(f"Nie udało się wygenerować wstępnego PDF dla pliku {html_path}")
            return None

        logger.info(f"Wstępny PDF został wygenerowany: {initial_pdf}")

        # Następnie obetnij PDF do rzeczywistej wysokości zawartości
        logger.info(f"Obcinanie PDF do rzeczywistej wysokości zawartości...")

        try:
            # Przycinanie PDF bez zmiany nazwy pliku (nadpisanie)
            trimmed_pdf = trim_existing_pdf(initial_pdf)

            if trimmed_pdf:
                logger.info(f"PDF został pomyślnie przycięty: {trimmed_pdf}")
                return trimmed_pdf
            else:
                logger.warning(f"Nie udało się przyciąć PDF, zwracam oryginalny plik: {initial_pdf}")
                return initial_pdf

        except Exception as e:
            logger.error(f"Błąd podczas przycinania PDF: {str(e)}")
            logger.info(f"Zwracam oryginalny PDF: {initial_pdf}")
            return initial_pdf

    except asyncio.CancelledError:
        logger.error(f"Operacja generowania PDF została przerwana")
        return None
    except Exception as e:
        logger.error(f"Błąd podczas generowania PDF: {str(e)}")
        return None


from zpl.zpl_file import *

from zebrafy import ZebrafyPDF
from decimal import Decimal

import decimal
import pikepdf
from zebrafy import ZebrafyPDF


def convert_to_float(value):
    """
    Kompleksowa konwersja różnych typów na float.

    :param value: Wartość do konwersji
    :return: Wartość jako float
    """
    if value is None:
        return 0.0

    try:
        # Obsługa decimal.Decimal
        if isinstance(value, decimal.Decimal):
            return float(value)

        # Obsługa int i float
        if isinstance(value, (int, float)):
            return float(value)

        # Próba rzutowania innych typów
        return float(value)
    except (TypeError, ValueError):
        raise TypeError(f"Nie można skonwertować wartości {value} do float")


def convert_pdf_to_zpl_with_original_dimensions(pdf_path, dpi=203, split_pages=False):
    """
    Konwertuje PDF do ZPL zachowując oryginalne wymiary strony.
    Implementuje komendę ZPL LL do ustawienia długości etykiety.

    :param pdf_path: Ścieżka do pliku PDF
    :param dpi: Rozdzielczość wydruku (domyślnie 203 DPI)
    :param split_pages: Czy rozdzielać strony (domyślnie False)
    :return: Ciąg znaków ZPL
    """
    # Otwórz PDF za pomocą pikepdf, aby uzyskać dokładne wymiary
    pdf = pikepdf.Pdf.open(pdf_path)

    # Pobierz rozmiary pierwszej strony
    # Uwaga: pikepdf używa punktów (1/72 cala), więc konwertujemy do milimetrów
    first_page = pdf.pages[0]
    width_pts = convert_to_float(first_page.mediabox[2] - first_page.mediabox[0])
    height_pts = convert_to_float(first_page.mediabox[3] - first_page.mediabox[1])

    # Bezpieczna konwersja punktów do milimetrów (1 punkt = 0.352778 mm)
    width_mm = int(width_pts * 2.54)
    height_mm = int(height_pts * 2.54)

    # print(f"Width: {width_mm}mm, Height: {height_mm}mm")
    # print(f"DPI: {dpi}, Split pages: {split_pages}")

    # Wczytaj zawartość PDF
    with open(pdf_path, "rb") as pdf_file:
        pdf_content = pdf_file.read()

    # Konwersja do ZPL z zachowaniem wymiarów
    zpl_string = ZebrafyPDF(
        pdf_content,
        format="ASCII",  # Format wyjściowy
        invert=True,  # Inwersja kolorów (dla etykiet)
        dither=False,  # Bez rozmycia
        threshold=128,  # Próg binaryzacji
        dpi=dpi,  # Rozdzielczość wydruku
        pos_x=9,  # Pozycja X
        pos_y=9,  # Pozycja Y
        rotation=0,  # Bez rotacji
        complete_zpl=True,  # Pełny kod ZPL
        split_pages=split_pages,  # Podział stron
        width=width_mm,  # Szerokość etykiety w mm
        height=height_mm  # Wysokość etykiety w mm
    ).to_zpl()

    # Sprawdź, czy ZPL zawiera już komendę LL
    if "^LL" not in zpl_string:
        # Konwersja wysokości z mm na dots (punkty) dla ZPL
        # ZPL używa jednostek w dots, a nie mm. Przy 203 DPI, 1 mm = 8 dots
        #height_dots = int(height_mm * (dpi / 25.4))  # 25.4mm = 1 cal
        height_dots = int(height_mm)
        # print(height_dots)
        # Dodaj komendę LL do ZPL - wstawia po komendzie ^LH (Label Home)
        if "^LH" in zpl_string:
            zpl_parts = zpl_string.split("^LH", 1)
            lh_parts = zpl_parts[1].split(",", 1)
            if len(lh_parts) > 1:
                # Wstaw po ^LH0,0
                insert_point = len(zpl_parts[0]) + len("^LH") + len(lh_parts[0]) + 1
                zpl_string = zpl_string[:insert_point] + f"^LL{height_dots}" + zpl_string[insert_point:]
            else:
                # Wstaw po ^LH
                insert_point = len(zpl_parts[0]) + len("^LH")
                zpl_string = zpl_string[:insert_point] + f"^LL{height_dots}" + zpl_string[insert_point:]
        # Jeśli nie ma ^LH, dodaj po ^XA
        elif "^XA" in zpl_string:
            insert_point = zpl_string.find("^XA") + len("^XA")
            zpl_string = zpl_string[:insert_point] + f"^LL{height_dots}" + zpl_string[insert_point:]

    return zpl_string


def safe_convert_pdf_to_zpl(pdf_path, logger=None, **kwargs):
    """
    Bezpieczna funkcja konwersji PDF do ZPL z obsługą błędów.

    :param pdf_path: Ścieżka do pliku PDF
    :param logger: Opcjonalny logger do rejestracji zdarzeń
    :param kwargs: Dodatkowe argumenty dla convert_pdf_to_zpl_with_original_dimensions
    :return: Słownik z wynikiem konwersji
    """
    try:
        # Próba konwersji PDF do ZPL
        zpl_string = convert_pdf_to_zpl_with_original_dimensions(pdf_path, **kwargs)

        return {
            'success': True,
            'zpl_string': zpl_string
        }
    except Exception as e:
        # Szczegółowa obsługa błędów
        error_msg = f"Błąd konwersji PDF do ZPL: {str(e)}"

        # Dodatkowe informacje diagnostyczne
        if logger:
            import traceback
            logger.error(error_msg)
            logger.error(f"Pełny ślad błędu:\n{traceback.format_exc()}")

        return {
            'success': False,
            'error': error_msg
        }


def process_pdf_to_zpl(pdf_path, zo_zpl, logger=None, **kwargs):
    """
    Przetwarza plik PDF na ZPL z obsługą błędów.
    Zapewnia prawidłowe przekazanie parametrów DPI dla komend LL (Label Length).

    :param pdf_path: Ścieżka do pliku PDF
    :param zo_zpl: Ścieżka do zapisu pliku ZPL
    :param logger: Opcjonalny logger
    :param kwargs: Dodatkowe argumenty dla konwersji
    :return: Wynik operacji
    """
    # Usuń argument 'config' z kwargs, jeśli istnieje
    configs = kwargs.pop('config', None)

    # Pobierz dpi z konfiguracji, jeśli nie podano w kwargs
    if 'dpi' not in kwargs and configs:
        kwargs['dpi'] = config.get_printer_dpi()

    # Wywołanie bezpiecznej konwersji
    conversion_result = safe_convert_pdf_to_zpl(pdf_path, logger, **kwargs)

    if conversion_result['success']:
        try:
            # Zapis wygenerowanego ZPL
            with open(zo_zpl, "w", encoding='utf-8') as zpl_file:
                zpl_file.write(conversion_result['zpl_string'])

            if logger:
                logger.info(f"Pomyślnie wygenerowano plik ZPL: {zo_zpl}")

            # Walidacja pliku ZPL
            result = validate_zpl_file(zo_zpl)
            if not result['success']:
                if logger:
                    for issue in result['issues']:
                        if issue['type'] == 'error':
                            logger.error(f"BŁĄD: {issue['message']}")
                        else:
                            logger.warning(f"UWAGA: {issue['message']}")

                    # Naprawa pliku ZPL
                    repair_result = repair_zpl_file(zo_zpl)
                    if repair_result['success']:
                        logger.info(f"Status: {repair_result['message']}")
                        if repair_result['fixed_issues']:
                            logger.info("Naprawione problemy:")
                            for fix in repair_result['fixed_issues']:
                                logger.info(f"- {fix}")

            return {
                'success': True,
                'message': f"Plik ZPL utworzony: {zo_zpl}"
            }
        except Exception as e:
            error_msg = f"Błąd podczas zapisu pliku ZPL: {str(e)}"

            # Dodatkowe informacje diagnostyczne
            if logger:
                import traceback
                logger.error(error_msg)
                logger.error(f"Pełny ślad błędu:\n{traceback.format_exc()}")

            return {
                'success': False,
                'error': error_msg
            }
    else:
        # Zwróć informację o błędzie konwersji
        return {
            'success': False,
            'error': conversion_result['error']
        }

# Inicjalizacja konfiguracji
config = ConfigManager()
config.load_config()
logger.info("Wczytano konfigurację")

zpl_dir = config.get_zo_zpl_dir()
# Pobierz parametry drukarki z konfiguracji
dpi = config.get_printer_dpi()
printer_ip = config.get_thermal_printer_ip()
printer_port = config.get_thermal_printer_port()
printer_name = config.get_thermal_printer_name()

def main():
    """
    Główna funkcja skryptu. Uruchamia proces generowania i drukowania zamówień.
    Wykorzystuje drukowanie ZPL przez sieć zamiast print_pdf_directly.
    """
    logger.info("Rozpoczęcie wykonywania skryptu")

    try:


        # Sprawdź, czy zdefiniowano adres IP drukarki
        if not printer_ip:
            logger.warning("Brak adresu IP drukarki w konfiguracji. Drukowanie sieciowe nie będzie działać.")
        else:
            logger.info(f"Wykryto drukarkę sieciową: {printer_ip}:{printer_port}")

        # Inicjalizacja menedżera drukarek termicznych (dla lokalnych drukarek)
        printer_manager = initialize_thermal_printer_manager(config)

        # Sprawdzenie, czy menedżer drukarek został prawidłowo zainicjalizowany
        if printer_manager is None and not printer_ip:
            logger.error(
                "Nie można zainicjalizować menedżera drukarek lokalnych i brak konfiguracji drukarki sieciowej.")
            logger.error("Zatrzymuję skrypt, ponieważ drukowanie nie będzie możliwe.")
            return

        # Generowanie connection string
        conn_str = config.get_connection_string()
        logger.info("Wygenerowano connection string")

        # Inicjalizacja połączenia z bazą danych
        db_manager = DatabaseManager(conn_str)
        db_manager.connect()
        logger.info("Połączono z bazą danych")



        # Pobierz listę już wydrukowanych zamówień
        printed_orders = get_printed_orders()
        logger.info(f"Znaleziono {len(printed_orders)} wydrukowanych zamówień")




        # Pobierz nazwę drukarki termicznej z config.ini (dla lokalnych drukarek)
        printer_name = None
        if printer_manager:
            printer_name = config.get_thermal_printer_name()
            if not printer_name:
                logger.warning("Brak dostępnej drukarki lokalnej w konfiguracji.")
                printer_name = printer_manager.get_default_thermal_printer()
                if printer_name:
                    logger.info(f"Używam domyślnej drukarki: {printer_name}")

        if not printer_name and not printer_ip:
            logger.error("Brak dostępnej drukarki (lokalnej lub sieciowej). Zatrzymuję skrypt.")
            return

        # Przetwórz dzisiejsze zamówienia
        #for order_number, html_content in process_todays_orders(db_manager, printed_orders):
        for order_number, html_content in process_todays_orders():
            try:
                # Zapisz plik HTML
                zo_html = save_order_html(order_number, html_content)
                logger.info(f"Zapisano plik HTML dla zamówienia {order_number}")

                # Pobierz parametry drukarki z konfiguracji
                dpi = config.get_printer_dpi()
                label_margin = config.get_printer_label_margin()
                label_width = config.get_printer_label_width()
                label_width_mm = config.get_printer_label_width_mm()
                label_height = config.get_printer_label_height()
                folder_prefix = config.get_printer_folder_prefix()

                # Określ ścieżkę pliku PDF
                zo_pdf = get_path_order(order_number, get_zo_pdf_dir(), '.pdf')

                # Generuj PDF z dwuetapowym procesem: html_to_pdf + html_to_continuous_pdf
                try:
                    # Użyj kontekstu timeout, aby zapobiec zawieszeniu
                    pdf_path = asyncio.run(generate_pdf(
                        zo_html,
                        zo_pdf,
                        label_width_mm=label_width_mm,
                        continuous=True,
                        margins={"top": 0, "right": 0, "bottom": 0, "left": 0}
                    ))
                except KeyboardInterrupt:
                    logger.warning("Przerwano generowanie PDF. Kontynuowanie przetwarzania zamówień...")
                    continue

                if pdf_path:
                    logger.info(f"PDF dla zamówienia {order_number} został wygenerowany: {pdf_path}")

                    # Określ ścieżkę pliku ZPL
                    zo_zpl = get_path_order(order_number, get_zo_zpl_dir(), '.zpl')
                    os.makedirs(os.path.dirname(zo_zpl), exist_ok=True)

                    # Generowanie ZPL z PDF
                    try:
                        # Generowanie ZPL z PDF
                        # with open(pdf_path, "rb") as pdf:
                        #     zpl_string = ZebrafyPDF(
                        #         pdf.read(),
                        #         format="ASCII",
                        #         invert=True,
                        #         dither=False,
                        #         threshold=128,
                        #         dpi=dpi,
                        #         pos_x=0,
                        #         pos_y=0,
                        #         rotation=0,
                        #         complete_zpl=True,
                        #         split_pages=False,
                        #         width=0,
                        #         height=0,
                        #     ).to_zpl()
                        #
                        # # Zapisz plik ZPL
                        # os.makedirs(os.path.dirname(zo_zpl), exist_ok=True)
                        # with open(zo_zpl, "w") as zpl_file:
                        #     zpl_file.write(zpl_string)
                        result = process_pdf_to_zpl(
                            pdf_path=zo_pdf,
                            zo_zpl=zo_zpl,
                            logger=logger,
                            config=config
                        )

                        if not result['success']:
                            logger.error(f"Nie udało się utworzyć pliku ZPL dla zamówienia {order_number}")
                            continue

                    except Exception as e:
                        logger.error(f"Błąd podczas generowania lub zapisywania ZPL: {str(e)}")
                    # Sprawdź, czy plik ZPL został utworzony
                    if not os.path.exists(zo_zpl):
                        logger.error(f"Nie udało się utworzyć pliku ZPL dla zamówienia {order_number}")
                        continue

                    id_uzytkownika = str(get_id_uzytkownika_by_order(order_number))
                    allowed_users = config.get_allowed_users()
                    # Convert all allowed users to strings for consistent comparison
                    allowed_users_str = [str(user_id) for user_id in allowed_users]

                    if id_uzytkownika not in allowed_users_str:
                        logger.error(
                            f"Nie udało się wydrukować zamówienia {order_number}, id_uzytkownika ({id_uzytkownika}) nie znajduje się na liście dozwolonych użytkowników: {allowed_users_str}")
                        continue
                    else:
                        logger.info(
                            f"Zamówienie {order_number}, id_uzytkownika: ({id_uzytkownika}) - użytkownik z uprawnieniami do drukowania")


                    # Drukowanie pliku ZPL na drukarce sieciowej lub lokalnej                    result = None
                    if printer_ip:
                        # Użyj drukowania sieciowego
                        result = print_zpl_network(zo_zpl, config)
                    elif printer_manager and printer_name:
                        # Użyj standardowego drukowania lokalnego (poprzez ThermalPrinterManager)
                        result = printer_manager.print_zpl_file(zo_zpl, printer_name)
                    else:
                        logger.error("Brak skonfigurowanej drukarki (sieciowej lub lokalnej)")
                        continue

                    # Obsługa wyniku drukowania
                    if result is not None and result.get('success', False):
                        logger.info(f"Zamówienie {order_number} zostało pomyślnie wydrukowane.")


                        # Zapisz kopię wydrukowanego pliku
                        zo_printed = get_path_order(order_number, get_printer_folder(config), '.zpl')
                        try:
                            import shutil
                            shutil.copy2(zo_zpl, zo_printed)
                            logger.debug(f"Zapisano ZPL to printer folder: {zo_printed}")
                        except:
                            pass
                        # with open(zo_printed, "w") as zpl_printed:
                        #     zpl_printed.write(zpl_string)

                        logger.info(f"Plik {zo_zpl} został wydrukowany i zapisano kopię w {zo_printed}")
                    else:
                        error_msg = "Nieznany błąd"
                        if result is not None and 'message' in result:
                            error_msg = result['message']
                        logger.error(f"Nie udało się wydrukować zamówienia {order_number}: {error_msg}")
                else:
                    logger.error(f"Nie udało się wygenerować PDF dla zamówienia {order_number}")

            except Exception as e:
                logger.exception(f"Błąd podczas przetwarzania zamówienia {order_number}: {str(e)}")

    except Exception as e:
        logger.error(f"Wystąpił błąd: {str(e)}", exc_info=True)
    finally:
        # Zamknij połączenia
        if 'db_manager' in locals():
            db_manager.close()
            logger.info("Zamknięto połączenie z bazą danych")


def get_printer_folder(config):
    folder_prefix = config.get_printer_folder_prefix()
    printer_name = config.get_thermal_printer_name()
    printer_id = printer_ip if printer_ip else normalize_filename(printer_name)
    zo_prt = f"{folder_prefix}{printer_id}"
    # Utwórz folder dla wydrukowanych plików
    os.makedirs(zo_prt, exist_ok=True)

    return zo_prt

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Skrypt został przerwany przez użytkownika (Ctrl+C)")
        sys.exit(0)