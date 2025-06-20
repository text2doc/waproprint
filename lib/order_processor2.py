#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do pobierania zamówień z bazy danych i zapisywania ich do plików JSON.
Używa tych samych ścieżek co skrypt sql2html.py.
"""

from datetime import datetime
import json
import os
import sys
import logging
from decimal import Decimal

# Importy z oryginalnego projektu
try:
    from lib.DatabaseManager import DatabaseManager
    from lib.ConfigManager import ConfigManager
    from lib.file_utils import get_zo_html_dir, get_zo_json_dir, normalize_filename, get_path_order, get_printed_orders
    from lib.logger import logger
    from lib.html_generator import generate_order_html
except ImportError:
    # Dodajemy bieżący katalog do ścieżki
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from lib.DatabaseManager import DatabaseManager
        from lib.ConfigManager import ConfigManager
        from lib.file_utils import get_zo_html_dir, get_zo_json_dir, normalize_filename, get_path_order, \
            get_printed_orders
        from lib.logger import logger
        from lib.html_generator import generate_order_html
    except ImportError:
        # Własne implementacje jeśli import się nie udał
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('order_retriever.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger('order_retriever')



        def get_zo_json_dir():
            config = ConfigManager()
            return config.config.get('Directories', 'JsonDir', fallback='orders_json')


        def get_zo_html_dir():
            config = ConfigManager()
            return config.config.get('Directories', 'HtmlDir', fallback='orders_html')


        def get_path_order(order_number, directory, extension):
            normalized_name = normalize_filename(order_number)
            os.makedirs(directory, exist_ok=True)
            return os.path.join(directory, f"{normalized_name}{extension}")


        def get_printed_orders():
            printed_dir = "printed_orders"
            if not os.path.exists(printed_dir):
                os.makedirs(printed_dir)
                return set()

            printed_orders = set()
            for filename in os.listdir(printed_dir):
                if filename.endswith('.zpl'):
                    order_number = os.path.splitext(filename)[0]
                    printed_orders.add(order_number)
            return printed_orders


        class DatabaseManager:
            def __init__(self, connection_string):
                self.connection_string = connection_string
                self.connection = None

            def connect(self):
                try:
                    import pyodbc
                    self.connection = pyodbc.connect(self.connection_string)
                    logger.info("Połączono z bazą danych")
                    return True
                except Exception as e:
                    logger.error(f"Błąd podczas łączenia z bazą danych: {str(e)}", exc_info=True)
                    return False

            def close(self):
                if self.connection:
                    self.connection.close()
                    logger.info("Zamknięto połączenie z bazą danych")


        class ConfigManager:
            def __init__(self, config_file='config.ini'):
                import configparser
                self.config_file = config_file
                self.config = configparser.ConfigParser()
                self.load_config()

            def load_config(self):
                try:
                    self.config.read(self.config_file)
                    logger.info(f"Wczytano konfigurację z pliku {self.config_file}")
                except Exception as e:
                    logger.error(f"Błąd podczas wczytywania konfiguracji: {str(e)}", exc_info=True)

            def get_connection_string(self):
                try:
                    driver = self.config.get('DATABASE', 'driver', fallback='{SQL Server}')
                    server = self.config.get('DATABASE', 'server')
                    database = self.config.get('DATABASE', 'database')
                    uid = self.config.get('DATABASE', 'UID', fallback='')
                    pwd = self.config.get('DATABASE', 'PWD', fallback='')
                    trusted_connection = self.config.get('DATABASE', 'trusted_connection', fallback='no')

                    if trusted_connection.lower() == 'yes':
                        return f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes'
                    else:
                        return f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
                except Exception as e:
                    logger.error(f"Błąd podczas generowania connection string: {str(e)}", exc_info=True)
                    return None


        def generate_order_html(order_data, items):
            """Prosta implementacja generowania HTML dla zamówienia."""
            html = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Zamówienie {order_data.get('NUMER', 'Brak numeru')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                </style>
            </head>
            <body>
                <h1>Zamówienie: {order_data.get('NUMER', 'Brak numeru')}</h1>
                <p>Data: {order_data.get('DATA_UTWORZENIA_WIERSZA', 'Brak daty')}</p>
                <p>Kontrahent: {order_data.get('KONTRAHENT_NAZWA', order_data.get('NAZWA', 'Brak nazwy kontrahenta'))}</p>

                <h2>Pozycje zamówienia:</h2>
                <table>
                    <tr>
                        <th>LP</th>
                        <th>Kod artykułu</th>
                        <th>Nazwa</th>
                        <th>Ilość</th>
                        <th>Cena netto</th>
                        <th>Cena brutto</th>
                    </tr>
            """

            for i, item in enumerate(items):
                html += f"""
                    <tr>
                        <td>{i + 1}</td>
                        <td>{item.get('INDEKS_KATALOGOWY', item.get('ID_ARTYKULU', ''))}</td>
                        <td>{item.get('NAZWA', 'Brak nazwy')}</td>
                        <td>{item.get('ZAMOWIONO', '0')}</td>
                        <td>{item.get('CENA_NETTO', '0.00')}</td>
                        <td>{item.get('CENA_BRUTTO', '0.00')}</td>
                    </tr>
                """

            html += """
                </table>
            </body>
            </html>
            """

            return html


def convert_decimal_to_str(obj):
    """
    Rekurencyjnie konwertuje wszystkie wartości typu Decimal, datetime i type na stringi.

    Args:
        obj: Obiekt do konwersji

    Returns:
        Obiekt z przekonwertowanymi wartościami
    """
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, type):
        return obj.__name__  # Konwertuj typy na ich nazwy
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_str(item) for item in obj]
    return obj


def get_id_uzytkownika_by_order(order_number):
    """
    Pobiera ID użytkownika na podstawie numeru zamówienia.
    """
    # Inicjalizacja konfiguracji jeśli nie podano
    config = ConfigManager()
    conn_str = config.get_connection_string()
    if not conn_str:
        logger.error("Nie udało się pobrać connection string")
        return

    db_manager = DatabaseManager(conn_str)
    if not db_manager.connect():
        logger.error("Nie udało się połączyć z bazą danych")
        return

    cursor = db_manager.connection.cursor()
    try:
        query = """
            SELECT ID_UZYTKOWNIKA FROM ZAMOWIENIE WHERE NUMER = ?
        """
        cursor.execute(query, (order_number))
        result = cursor.fetchone()
        if result:
            logger.info(f"ID użytkownika: {result[0]} dla zamówienia o numerze {order_number}")
            return result[0]
        else:
            logger.warning(f"Nie znaleziono użytkownika dla zamówienia o numerze {order_number}")
            return None
    except Exception as e:
        logger.error(f"Błąd podczas pobierania zamówienia {order_number}: {str(e)}", exc_info=True)
        return None


def get_order_by_number(db_connection, order_number):
    """
    Pobiera dane zamówienia na podstawie numeru.

    Args:
        db_connection: Połączenie z bazą danych
        order_number (str): Numer zamówienia

    Returns:
        dict: Dane zamówienia lub None, jeśli nie znaleziono
    """
    cursor = db_connection.cursor()

    try:
        # Pobierz dane zamówienia
        query = """
            SELECT * FROM ZAMOWIENIE WHERE NUMER = ?
        """
        cursor.execute(query, (order_number,))
        order_row = cursor.fetchone()

        if not order_row:
            logger.warning(f"Nie znaleziono zamówienia o numerze {order_number}")
            return None

        # Konwertujemy wiersz na słownik
        order_columns = [column[0] for column in cursor.description]
        order_data = {order_columns[i]: value for i, value in enumerate(order_row)}

        # Pobierz dane kontrahenta
        kontrahent_id = order_data.get('ID_KONTRAHENTA')
        kontrahent_data = {}

        if kontrahent_id:
            query = """
                SELECT * FROM KONTRAHENT WHERE ID_KONTRAHENTA = ?
            """
            cursor.execute(query, (kontrahent_id,))
            kontrahent_row = cursor.fetchone()

            if kontrahent_row:
                kontrahent_columns = [column[0] for column in cursor.description]
                kontrahent_data = {kontrahent_columns[i]: value for i, value in enumerate(kontrahent_row)}

                # Dodaj dane kontrahenta jako podsłownik
                order_data['kontrahent'] = kontrahent_data

        # Log diagnostyczny
        logger.info(f"Kod kreskowy zamówienia: {order_data.get('KOD_KRESKOWY', '')}")
        logger.info(f"Kod kreskowy kontrahenta: {kontrahent_data.get('KOD_KRESKOWY', '')}")

        # Pobieramy pozycje zamówienia
        order_id = order_data.get('ID_ZAMOWIENIA')
        if not order_id:
            logger.warning(f"Zamówienie {order_number} nie ma ID_ZAMOWIENIA")
            return {'order': order_data, 'items': []}

        # Pobierz pozycje zamówienia
        query = """
            SELECT * FROM POZYCJA_ZAMOWIENIA WHERE ID_ZAMOWIENIA = ? ORDER BY ID_POZYCJI_ZAMOWIENIA
        """
        cursor.execute(query, (order_id,))
        position_rows = cursor.fetchall()
        position_columns = [column[0] for column in cursor.description]

        # Konwertujemy pozycje na listę słowników
        items = []
        for row in position_rows:
            position_dict = {position_columns[i]: value for i, value in enumerate(row)}

            # Zachowaj wartości z pozycji zamówienia
            zamowiono = position_dict.get('ZAMOWIONO')
            zrealizowano = position_dict.get('ZREALIZOWANO')

            # Pobierz dane artykułu
            article_id = position_dict.get('ID_ARTYKULU')
            if article_id:
                query = """
                    SELECT * FROM ARTYKUL WHERE ID_ARTYKULU = ?
                """
                cursor.execute(query, (article_id,))
                article_row = cursor.fetchone()

                if article_row:
                    article_columns = [column[0] for column in cursor.description]

                    # Przygotuj pusty słownik dla połączonych danych
                    item_dict = {}

                    # Najpierw dodaj dane artykułu
                    for i, col_name in enumerate(article_columns):
                        item_dict[col_name] = article_row[i]

                    # Następnie dodaj/nadpisz dane pozycji zamówienia
                    for key, value in position_dict.items():
                        item_dict[key] = value

                    # Upewnij się, że wartości ZAMOWIONO i ZREALIZOWANO są poprawne
                    item_dict['ZAMOWIONO'] = zamowiono
                    item_dict['ZREALIZOWANO'] = zrealizowano

                    items.append(item_dict)
            else:
                # Jeśli nie ma artykułu, dodaj tylko dane pozycji
                items.append(position_dict)

        logger.info(f"Znaleziono {len(items)} pozycji dla zamówienia {order_number}")

        # Dodaj informacje diagnostyczne o każdej pozycji
        for i, item in enumerate(items):
            item_id = item.get('ID_ARTYKULU')
            item_name = item.get('NAZWA', 'Nieznany artykuł')
            zamowiono = item.get('ZAMOWIONO', 0)
            logger.info(f"Pozycja {i + 1}: ID={item_id}, Nazwa={item_name}, ZAMOWIONO={zamowiono}")

        # Przygotuj wynikowy słownik w oczekiwanym formacie
        result = {
            'order': order_data,
            'items': items
        }

        return result

    except Exception as e:
        logger.error(f"Błąd podczas pobierania zamówienia {order_number}: {str(e)}", exc_info=True)
        return None


def save_order_to_json(order_data, output_dir=None):
    """
    Zapisuje dane zamówienia do pliku JSON.
    Używa tych samych ścieżek co oryginalne skrypty.

    Args:
        order_data (dict): Dane zamówienia
        output_dir (str, optional): Katalog wyjściowy. Jeśli None, użyje get_zo_json_dir()

    Returns:
        str: Ścieżka do zapisanego pliku lub None w przypadku błędu
    """
    if not order_data:
        logger.warning("Próba zapisania pustych danych zamówienia")
        return None

    # Jeśli nie podano katalogu wyjściowego, użyj domyślnego
    if output_dir is None:
        output_dir = get_zo_json_dir()

    # Upewniamy się, że katalog istnieje
    os.makedirs(output_dir, exist_ok=True)

    # Pobieramy numer zamówienia
    try:
        # W zależności od struktury danych
        if isinstance(order_data, dict) and 'order' in order_data:
            # Format: {'order': {...}, 'items': [...]}
            order_number = order_data['order'].get('NUMER', 'unknown')
        elif isinstance(order_data, dict) and 'data' in order_data:
            # Format: {'data': {...}, 'items': [...], 'meta': {...}}
            order_number = order_data['data'].get('NUMER', 'unknown')
        else:
            # Stara struktura lub inna
            order_number = order_data.get('NUMER', 'unknown')
    except Exception as e:
        logger.error(f"Błąd podczas pobierania numeru zamówienia: {str(e)}")
        order_number = 'unknown'

    normalized_order_number = normalize_filename(order_number)
    logger.info(f"Sciezka pliku: {output_dir}\\{normalized_order_number}.json")

    # Konwertujemy wartości Decimal na stringi
    try:
        output_data = convert_decimal_to_str(order_data)
    except TypeError as e:
        logger.error(f"Błąd konwersji typów przy zapisie JSON: {str(e)}")
        # Prosta wersja konwersji jako zabezpieczenie
        output_data = json.loads(json.dumps(order_data, default=lambda o: str(o)))

    # Używamy tej samej konwencji nazewnictwa plików co w oryginalnym skrypcie
    output_file = get_path_order(order_number, output_dir, '.json')

    try:
        # Zapisujemy dane do pliku
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Obliczamy rozmiar pliku
        file_size = os.path.getsize(output_file)

        logger.info(f"Zapisano dane zamówienia {order_number} do pliku {output_file} (rozmiar: {file_size} bajtów)")

        # Wyświetl podsumowanie pozycji
        items = []
        if 'items' in output_data:
            items = output_data['items']

        total_items = len(items)
        logger.info(f"Podsumowanie: Zamówienie {order_number} zawiera {total_items} pozycji")

        # Sprawdź czy wszystkie pozycje mają kolumnę ZAMOWIONO
        if isinstance(items, list):
            missing_zamowiono = [i for i, item in enumerate(items) if 'ZAMOWIONO' not in item]
            if missing_zamowiono:
                logger.warning(f"Uwaga: {len(missing_zamowiono)} pozycji nie ma kolumny ZAMOWIONO")

        return output_file

    except Exception as e:
        logger.error(f"Błąd podczas zapisywania danych zamówienia {order_number}: {str(e)}", exc_info=True)
        return None


def generate_html_for_order(order_data):
    """
    Generuje HTML dla zamówienia na podstawie danych.

    Args:
        order_data (dict): Dane zamówienia

    Returns:
        str: Zawartość HTML dla zamówienia
    """
    try:
        # Sprawdź strukturę danych
        if isinstance(order_data, dict) and 'order' in order_data and 'items' in order_data:
            # Format: {'order': {...}, 'items': [...]}
            order_info = order_data['order']
            items = order_data['items']
        elif isinstance(order_data, dict) and 'data' in order_data:
            # Format: {'data': {...}, 'items': [...], 'meta': {...}}
            order_info = order_data['data']
            items = order_data.get('items', [])
        else:
            # Stara struktura
            order_info = order_data
            items = order_data.get('items', [])

        # Generuj HTML
        html_content = generate_order_html(order_data=order_info, items=items)
        return html_content

    except Exception as e:
        logger.error(f"Błąd podczas generowania HTML: {str(e)}", exc_info=True)
        # Zwróć podstawowy HTML w przypadku błędu
        return f"""
        <html>
        <head><title>Błąd Generowania</title></head>
        <body>
            <h1>Błąd podczas generowania zamówienia</h1>
            <p>Wystąpił błąd: {str(e)}</p>
        </body>
        </html>
        """


def get_todays_orders(db_connection):
    """
    Pobiera numery zamówień z dzisiejszego dnia.

    Args:
        db_connection: Połączenie z bazą danych

    Returns:
        list: Lista numerów zamówień z dzisiejszego dnia
    """
    cursor = db_connection.cursor()

    try:
        query = """
            SELECT NUMER, ID_ZAMOWIENIA, DATA_UTWORZENIA_WIERSZA
            FROM ZAMOWIENIE 
            WHERE CAST(DATA_UTWORZENIA_WIERSZA AS date) = CAST(GETDATE() AS date)
            ORDER BY DATA_UTWORZENIA_WIERSZA ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Pobieramy numer zamówienia oraz dodatkowe informacje
        order_details = []
        for row in rows:
            if row[0]:  # Jeśli numer zamówienia istnieje
                order_details.append({
                    'numer': row[0],
                    'id_zamowienia': row[1],
                    'data_utworzenia': row[2]
                })

        # Tworzymy listę numerów zamówień
        order_numbers = [detail['numer'] for detail in order_details]

        logger.info(f"Znaleziono {len(order_numbers)} zamówień z dzisiejszego dnia")

        # Wyświetl szczegóły zamówień
        logger.info("Szczegóły znalezionych zamówień:")
        for i, detail in enumerate(order_details):
            logger.info(
                f"{i + 1}. NUMER: {detail['numer']}, ID: {detail['id_zamowienia']}, DATA: {detail['data_utworzenia']}")

        return order_numbers

    except Exception as e:
        logger.error(f"Błąd podczas pobierania dzisiejszych zamówień: {str(e)}", exc_info=True)
        return []


def process_todays_orders(db_manager=None, printed_orders=None):
    """
    Przetwarza zamówienia z dzisiejszego dnia.

    Args:
        db_manager: Instancja DatabaseManager
        printed_orders: Zbiór identyfikatorów już wydrukowanych zamówień

    Yields:
        tuple: Para (order_number, html_content) dla każdego przetworzonego zamówienia
    """
    # Inicjalizacja konfiguracji jeśli nie podano
    if db_manager is None:
        config = ConfigManager()
        conn_str = config.get_connection_string()
        if not conn_str:
            logger.error("Nie udało się pobrać connection string")
            return

        db_manager = DatabaseManager(conn_str)
        if not db_manager.connect():
            logger.error("Nie udało się połączyć z bazą danych")
            return

    # Inicjalizacja zbioru wydrukowanych zamówień jeśli nie podano
    if printed_orders is None:
        printed_orders = get_printed_orders()
        logger.info(f"Znaleziono {len(printed_orders)} już wydrukowanych zamówień")

    try:
        # Pobierz dzisiejsze zamówienia
        order_numbers = get_todays_orders(db_manager.connection)

        # Jeśli brak zamówień, zakończ
        if not order_numbers:
            logger.info("Brak zamówień z dzisiejszego dnia")
            return

        # Przetwórz każde zamówienie
        for order_number in order_numbers:
            try:
                # Sprawdź czy zamówienie było już wydrukowane
                normalized_number = normalize_filename(order_number)
                # if normalized_number started not from ZO do not print
                if not normalized_number.startswith('ZO'):
                    logger.info(f"Zamówienie {order_number} nie zaczyna sie od ZO ... , pomijam...")
                    continue

                if normalized_number in printed_orders:
                    logger.info(f"Zamówienie {order_number} zostało już wydrukowane, pomijam...")
                    continue

                logger.info(f"Przetwarzanie zamówienia {order_number}")

                # Pobierz dane zamówienia
                order_data = get_order_by_number(db_manager.connection, order_number)

                if not order_data:
                    logger.warning(f"Nie znaleziono danych dla zamówienia {order_number}")
                    continue

                # Zapisz dane do JSON
                json_file = save_order_to_json(order_data)

                if not json_file:
                    logger.error(f"Nie udało się zapisać danych zamówienia {order_number} do pliku JSON")
                    continue

                # Generuj HTML dla zamówienia
                html_content = generate_html_for_order(order_data)

                if not html_content:
                    logger.error(f"Nie udało się wygenerować HTML dla zamówienia {order_number}")
                    continue

                # Zwróć parę (order_number, html_content)
                logger.info(f"Przygotowano zamówienie {order_number} do wydruku")
                yield (order_number, html_content)

            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania zamówienia {order_number}: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Błąd podczas wykonywania skryptu: {str(e)}", exc_info=True)
    finally:
        # Nie zamykamy połączenia jeśli zostało przekazane z zewnątrz
        pass


def main():
    """Główna funkcja skryptu do uruchamiania autonomicznego."""
    config = ConfigManager()
    conn_str = config.get_connection_string()

    if not conn_str:
        logger.error("Nie udało się pobrać connection string")
        return

    db_manager = DatabaseManager(conn_str)
    if not db_manager.connect():
        logger.error("Nie udało się połączyć z bazą danych")
        return

    try:
        # Pobierz listę już wydrukowanych zamówień
        printed_orders = get_printed_orders()

        # Przetwórz zamówienia
        for order_number, html_content in process_todays_orders(db_manager, printed_orders):
            logger.info(f"Wynik przetwarzania zamówienia: {order_number}")

            # Tutaj możesz dodać dodatkową logikę przetwarzania zamówień
            # np. zapis HTML do pliku, generowanie PDF, itp.
            html_dir = get_zo_html_dir()
            html_file = get_path_order(order_number, html_dir, '.html')

            try:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"Zapisano HTML do pliku {html_file}")
            except Exception as e:
                logger.error(f"Nie udało się zapisać HTML dla zamówienia {order_number}: {str(e)}")

    except Exception as e:
        logger.error(f"Błąd podczas wykonywania skryptu: {str(e)}", exc_info=True)
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()