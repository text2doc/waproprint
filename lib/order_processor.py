#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import json
import os
import configparser
from decimal import Decimal

from .html_generator import generate_order_html
from .file_utils import normalize_filename, get_zo_html_dir, get_zo_json_dir
from .logger import logger

# Wczytaj konfigurację
config = configparser.ConfigParser()
config.read('config.ini')


def convert_decimal_to_str(obj):
    """
    Rekurencyjnie konwertuje wszystkie wartości typu Decimal i datetime na stringi.

    Args:
        obj: Obiekt do konwersji

    Returns:
        Obiekt z przekonwertowanymi wartościami Decimal i datetime
    """
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_str(item) for item in obj]
    return obj


def diagnose_order_items(db_connection, order_number):
    """
    Funkcja diagnostyczna do sprawdzania pozycji zamówienia.

    Args:
        db_connection: Połączenie z bazą danych
        order_number: Numer zamówienia do sprawdzenia

    Returns:
        dict: Informacje diagnostyczne o zamówieniu i jego pozycjach
    """
    cursor = db_connection.cursor()
    results = {}

    try:
        # 1. Znajdź ID_ZAMOWIENIA na podstawie numeru
        query = "SELECT ID_ZAMOWIENIA, NUMER FROM ZAMOWIENIE WHERE NUMER = ?"
        cursor.execute(query, (order_number,))
        order_row = cursor.fetchone()

        if not order_row:
            return {"error": f"Nie znaleziono zamówienia o numerze {order_number}"}

        order_id = order_row[0]
        results["order_info"] = {
            "ID_ZAMOWIENIA": order_id,
            "NUMER": order_row[1]
        }

        # 2. Sprawdź wszystkie pozycje zamówienia
        query = """
            SELECT 
                ID_POZYCJI_ZAMOWIENIA, 
                ID_ARTYKULU, 
                ZAMOWIONO, 
                ZREALIZOWANO, 
                DO_REALIZACJI, 
                ZAREZERWOWANO
            FROM POZYCJA_ZAMOWIENIA 
            WHERE ID_ZAMOWIENIA = ?
        """
        cursor.execute(query, (order_id,))
        item_rows = cursor.fetchall()

        results["total_items"] = len(item_rows)
        results["items"] = []

        for row in item_rows:
            results["items"].append({
                "ID_POZYCJI_ZAMOWIENIA": row[0],
                "ID_ARTYKULU": row[1],
                "ZAMOWIONO": float(row[2]) if row[2] is not None else None,
                "ZREALIZOWANO": float(row[3]) if row[3] is not None else None,
                "DO_REALIZACJI": float(row[4]) if row[4] is not None else None,
                "ZAREZERWOWANO": float(row[5]) if row[5] is not None else None
            })

        # 3. Sprawdź szczegóły artykułów
        if results["items"]:
            article_ids = [item["ID_ARTYKULU"]
                           for item in results["items"] if item["ID_ARTYKULU"] is not None]

            if article_ids:
                placeholder = ','.join(['?'] * len(article_ids))
                query = f"""
                    SELECT ID_ARTYKULU, NAZWA, ID_FIRMY, ID_MAGAZYNU
                    FROM ARTYKUL 
                    WHERE ID_ARTYKULU IN ({placeholder})
                """
                cursor.execute(query, article_ids)
                article_rows = cursor.fetchall()

                results["articles"] = []
                for row in article_rows:
                    results["articles"].append({
                        "ID_ARTYKULU": row[0],
                        "NAZWA": row[1],
                        "ID_FIRMY": row[2],
                        "ID_MAGAZYNU": row[3]
                    })

                # Sprawdź, czy artykuły istnieją w tabeli ARTYKUL
                found_article_ids = [article["ID_ARTYKULU"]
                                     for article in results["articles"]]
                missing_article_ids = [
                    id for id in article_ids if id not in found_article_ids]

                if missing_article_ids:
                    results["missing_articles"] = missing_article_ids

        return results

    except Exception as e:
        logger.error(
            f"Błąd podczas diagnostyki zamówienia {order_number}: {str(e)}", exc_info=True)
        return {"error": str(e)}


def load_orders_from_sql(db_connection, order_id=None):
    """
    Pobiera dane zamówienia z bazy SQL.

    Args:
        db_connection: Połączenie z bazą danych
        order_id (int, optional): ID zamówienia do pobrania. Jeśli None, pobiera wszystkie zamówienia

    Returns:
        list: Lista słowników zamówień
    """
    cursor = db_connection.cursor()

    try:
        # Tworzenie zapytania SQL dla głównych danych zamówienia
        if order_id:
            query = """
                SELECT Z.*, K.* FROM ZAMOWIENIE Z
                LEFT JOIN KONTRAHENT K ON Z.ID_KONTRAHENTA = K.ID_KONTRAHENTA
                WHERE Z.NUMER = ?
            """
            cursor.execute(query, (order_id,))
            logger.info(
                f"Wykonano zapytanie o zamówienie z numerem {order_id}")
        else:
            query = """
                SELECT Z.*, K.* FROM ZAMOWIENIE Z
                LEFT JOIN KONTRAHENT K ON Z.ID_KONTRAHENTA = K.ID_KONTRAHENTA
                ORDER BY Z.ID_ZAMOWIENIA
            """
            cursor.execute(query)
            logger.info("Wykonano zapytanie o wszystkie zamówienia")

        order_rows = cursor.fetchall()
        logger.info(
            f"Zapytanie zwróciło {len(order_rows)} wierszy dla zamówień")

        if not order_rows:
            logger.warning(f"Nie znaleziono zamówienia z numerem {order_id}")
            return []

        columns = [column[0] for column in cursor.description]

        orders = []
        for row in order_rows:
            order_dict = {columns[i]: value for i, value in enumerate(row)}
            orders.append(order_dict)

        # Dla każdego zamówienia pobierz jego pozycje
        for order in orders:
            # Pobranie ID_ZAMOWIENIA
            order_id_from_row = order.get('ID_ZAMOWIENIA')
            numer_zamowienia = order.get('NUMER', 'nieznany')

            logger.info(
                f"Zamówienie: NUMER={numer_zamowienia}, ID_ZAMOWIENIA={order_id_from_row}")

            # Najpierw sprawdź, czy istnieją jakiekolwiek pozycje dla tego zamówienia
            check_query = """
                SELECT COUNT(*) AS liczba_pozycji FROM POZYCJA_ZAMOWIENIA 
                WHERE ID_ZAMOWIENIA = ?
            """
            cursor.execute(check_query, (order_id_from_row,))
            count_row = cursor.fetchone()
            total_positions = count_row[0] if count_row else 0

            logger.info(
                f"Zamówienie {numer_zamowienia} ma łącznie {total_positions} pozycji w bazie")

            # Jeśli nie ma pozycji, zakończ przetwarzanie tego zamówienia
            if total_positions == 0:
                logger.warning(
                    f"Brak pozycji dla zamówienia {numer_zamowienia}, dodaję pustą listę")
                order['items'] = []
                continue

            # Pobierz wszystkie pozycje z wartością ZREALIZOWANO > 0
            # query = """
            #     SELECT PZ.*, A.*
            #     FROM POZYCJA_ZAMOWIENIA PZ
            #     LEFT JOIN ARTYKUL A ON PZ.ID_ARTYKULU = A.ID_ARTYKULU
            #     WHERE PZ.ID_ZAMOWIENIA = ?
            #     AND PZ.ZREALIZOWANO > 0
            #     ORDER BY PZ.ID_ARTYKULU
            # """
            # cursor.execute(query, (order_id_from_row,))
            # item_rows = cursor.fetchall()

            # logger.info(f"Zapytanie o pozycje z ZREALIZOWANO > 0 zwróciło {len(item_rows)} wierszy")

            # Jeśli nie ma pozycji z ZREALIZOWANO > 0, pobierz wszystkie pozycje
            # if len(item_rows) == 0:
            logger.warning(
                f"Brak pozycji z ZREALIZOWANO > 0, pobieram wszystkie pozycje")
            query = """
                SELECT PZ.*, A.*
                FROM POZYCJA_ZAMOWIENIA PZ
                LEFT JOIN ARTYKUL A ON PZ.ID_ARTYKULU = A.ID_ARTYKULU
                WHERE PZ.ID_ZAMOWIENIA = ?
                ORDER BY PZ.ID_POZYCJI_ZAMOWIENIA
            """
            cursor.execute(query, (order_id_from_row,))
            item_rows = cursor.fetchall()
            logger.info(
                f"Zapytanie o wszystkie pozycje zwróciło {len(item_rows)} wierszy")

            # Jeśli nadal nie ma pozycji, zakończ przetwarzanie tego zamówienia
            if not item_rows:
                logger.warning(
                    f"Nie znaleziono żadnych pozycji dla zamówienia {numer_zamowienia}")
                order['items'] = []
                continue

            columns = [column[0] for column in cursor.description]

            # Zbiór do śledzenia unikalnych ID artykułów
            # Zbiór do śledzenia unikalnych ID artykułów
            seen_article_ids = set()

            # Słownik do grupowania ilości według ID artykułu
            article_quantities = {}

            for row in item_rows:
                item_dict = {columns[i]: value for i, value in enumerate(row)}
                article_id = item_dict.get('ID_ARTYKULU')

                if article_id is None:
                    continue

                # Pobierz ilość zamówioną
                zamowiono_str = item_dict.get('ZAMOWIONO', '0')
                try:
                    zamowiono = float(str(zamowiono_str).replace(',', '.'))
                except (ValueError, TypeError):
                    zamowiono = 0

                # Dodaj lub zaktualizuj ilość dla tego artykułu
                if article_id in article_quantities:
                    article_quantities[article_id]['quantity'] += zamowiono
                    # Zachowaj najnowszą pozycję lub pozycję z najwyższą ilością
                    if zamowiono > 0:  # tylko aktualizuj, jeśli nowa ilość jest dodatnia
                        article_quantities[article_id]['item'] = item_dict
                else:
                    article_quantities[article_id] = {
                        'item': item_dict,
                        'quantity': zamowiono
                    }

            # Utwórz listę pozycji z zagregowanymi ilościami
            items = []
            for article_id, data in article_quantities.items():
                item = data['item']
                item['ZAMOWIONO'] = str(data['quantity'])
                items.append(item)

                # logger.info(f"Dodano pozycję: ID_ARTYKULU={article_id}, ZAMOWIONO={zamowiono}")
                logger.info(
                    f"Dodano pozycję: ID_ARTYKULU={article_id}, ZAMOWIONO={data['quantity']}")

            order['items'] = items
            logger.info(
                f"Dodano {len(items)} unikalnych pozycji do zamówienia {numer_zamowienia}")

        return orders

    except Exception as e:
        logger.error(
            f"Błąd podczas pobierania danych z SQL: {str(e)}", exc_info=True)
        return []


def get_todays_orders(db_connection):
    """
    Pobiera zamówienia z dzisiejszego dnia, sortując je od najstarszego.
    Rozróżnia kolumny o tych samych nazwach z różnych tabel.

    Args:
        db_connection: Połączenie z bazą danych

    Returns:
        list: Lista zamówień z dzisiejszego dnia z wyraźnie rozdzielonymi danymi tabel
    """
    cursor = db_connection.cursor()

    # Zamiast wymieniać wszystkie kolumny, używamy gwiazdki z aliasem tabeli
    # ale dodajemy jawnie tylko te kolumny, które mogą powodować konflikt
    query = """
        SELECT 
            Z.*,
            K.*,
            Z.KOD_KRESKOWY AS ZAMOWIENIE_KOD_KRESKOWY,
            K.KOD_KRESKOWY AS KONTRAHENT_KOD_KRESKOWY,
            K.ID_KONTRAHENTA AS K_ID_KONTRAHENTA,
            K.NAZWA AS K_NAZWA,
            K.FORMA_PLATNOSCI AS K_FORMA_PLATNOSCI
        FROM ZAMOWIENIE Z
        LEFT JOIN KONTRAHENT K ON Z.ID_KONTRAHENTA = K.ID_KONTRAHENTA
        WHERE CAST(Z.DATA_UTWORZENIA_WIERSZA AS date) = CAST(GETDATE() AS date)
        ORDER BY Z.DATA_UTWORZENIA_WIERSZA ASC
    """

    cursor.execute(query)
    order_rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    orders = []
    for row in order_rows:
        order_dict = {columns[i]: value for i, value in enumerate(row)}

        # Przetwarzamy słownik, aby oddzielić dane zamówienia i kontrahenta
        zamowienie_data = {}
        kontrahent_data = {}

        # Dla kolumn konflikujących, używamy aliasów
        konfliktujace_kolumny = {
            'KOD_KRESKOWY': ('ZAMOWIENIE_KOD_KRESKOWY', 'KONTRAHENT_KOD_KRESKOWY'),
            'ID_KONTRAHENTA': ('ID_KONTRAHENTA', 'K_ID_KONTRAHENTA'),
            'NAZWA': ('KONTRAHENT_NAZWA', 'K_NAZWA'),
            'FORMA_PLATNOSCI': ('FORMA_PLATNOSCI', 'K_FORMA_PLATNOSCI')
        }

        # Przygotowujemy strukture zamówienie/kontrahent
        for key, value in order_dict.items():
            # Obsługujemy kolumny z aliasami
            if key == 'ZAMOWIENIE_KOD_KRESKOWY':
                zamowienie_data['KOD_KRESKOWY'] = value
            elif key == 'KONTRAHENT_KOD_KRESKOWY':
                kontrahent_data['KOD_KRESKOWY'] = value
            elif key == 'K_ID_KONTRAHENTA':
                kontrahent_data['ID_KONTRAHENTA'] = value
            elif key == 'K_NAZWA':
                kontrahent_data['NAZWA'] = value
            elif key == 'K_FORMA_PLATNOSCI':
                kontrahent_data['FORMA_PLATNOSCI'] = value
            # Obsługujemy standardowe kolumny (nie z aliasami)
            elif key in konfliktujace_kolumny:
                # Jeśli to kolumna konflikująca bez aliasu, przypisujemy ją do zamówienia
                # (aliasowane wersje obsłużyliśmy już wyżej)
                zamowienie_data[key] = value
            # Pozostałe kolumny przypisujemy na podstawie prefiksu
            else:
                # Rozpoznawanie kolumn kontrahenta na podstawie znajomości struktury tabel
                # (w rzeczywistej implementacji można to robić dynamiczniej)
                kontrahent_kolumny = [
                    'WOJEWODZTWO', 'NAZWA_PELNA', 'ODBIORCA', 'DOSTAWCA', 'NIP', 'REGON',
                    'PLATNIK_VAT', 'LIMIT_KUPIECKI', 'TERMIN_NALEZNOSCI', 'TERMIN_ZOBOWIAZAN',
                    'DRUKUJ_OSTRZEZENIE', 'POKAZUJ_OSTRZEZENIE', 'OSTRZEZENIE', 'KOD_KONTRAHENTA',
                    'KOD_POCZTOWY', 'MIEJSCOWOSC', 'ULICA_LOKAL', 'ADRES_WWW', 'NIPL', 'DOS_KOD',
                    'WYROZNIK', 'KontrahentUE', 'KLUCZ', 'SYM_KRAJU_KOR', 'TELEFON_FIRMOWY'
                ]

                if key in kontrahent_kolumny:
                    kontrahent_data[key] = value
                else:
                    # Pozostałe kolumny przypisujemy do zamówienia
                    zamowienie_data[key] = value

        # Tworzymy finalny słownik z danymi
        final_order = {
            **zamowienie_data,  # Dane zamówienia na głównym poziomie
            'kontrahent': kontrahent_data  # Dane kontrahenta w podsekcji
        }

        orders.append(final_order)

    return orders


def save_order_to_json(order_data, order_items, output_dir=None):
    """
    Zapisuje dane zamówienia do pliku JSON.

    Args:
        order_data (dict): Dane zamówienia
        order_items (list): Lista pozycji zamówienia
        output_dir (str, optional): Katalog wyjściowy dla plików JSON. Jeśli None, użyje wartości z config.ini

    Returns:
        str: Znormalizowany numer zamówienia
    """
    if output_dir is None:
        output_dir = get_zo_json_dir()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    order_number = order_data.get('NUMER', '')
    normalized_order_number = normalize_filename(order_number)

    # Konwertuj wszystkie wartości Decimal na stringi
    output_data = {
        'order': convert_decimal_to_str(order_data),
        'items': convert_decimal_to_str(order_items)
    }

    output_file = os.path.join(output_dir, f"{normalized_order_number}.json")

    # Sprawdź czy plik JSON już istnieje i porównaj dane
    data_changed = False
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            # Porównaj dane
            if existing_data != output_data:
                data_changed = True
                logger.info(
                    f"Wykryto zmiany w danych zamówienia {order_number}")

        except Exception as e:
            logger.error(
                f"Błąd podczas porównywania danych dla zamówienia {order_number}: {str(e)}")
            data_changed = True
    else:
        data_changed = True
        logger.info(
            f"Tworzenie nowego pliku JSON dla zamówienia {order_number}")

    # Jeśli dane się zmieniły, zapisz nowy plik JSON
    if data_changed:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            logger.info(
                f"Zapisano zaktualizowane dane zamówienia {order_number} do pliku JSON")

            # Sprawdź czy istnieje plik HTML i usuń go jeśli dane się zmieniły

            # html_file = os.path.join(get_zo_html_dir(), f"{normalized_order_number}.html")
            # if os.path.exists(html_file):
            #     os.remove(html_file)
            #     logger.info(f"Usunięto stary plik HTML dla zamówienia {order_number} z powodu zmian w danych")

        except Exception as e:
            logger.error(
                f"Błąd podczas zapisywania danych dla zamówienia {order_number}: {str(e)}")
            return None

    return normalized_order_number


def convert_json_to_html(input_dir=None, output_dir=None):
    """
    Konwertuje pliki JSON z zamówieniami na pliki HTML.

    Args:
        input_dir (str, optional): Katalog z plikami JSON. Jeśli None, użyje wartości z config.ini
        output_dir (str, optional): Katalog wyjściowy dla plików HTML. Jeśli None, użyje wartości z config.ini
    """
    if input_dir is None:
        input_dir = get_zo_json_dir()
    if output_dir is None:
        output_dir = get_zo_html_dir()

    if not os.path.exists(input_dir):
        logger.error(f"Katalog {input_dir} nie istnieje")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if not filename.endswith('.json'):
            continue

        input_file = os.path.join(input_dir, filename)
        normalized_order_number = os.path.splitext(filename)[0]
        output_file = os.path.join(
            output_dir, f"{normalized_order_number}.html")

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Sprawdź czy plik HTML już istnieje
            if os.path.exists(output_file):
                logger.info(
                    f"Plik HTML dla zamówienia {normalized_order_number} już istnieje, pomijam generowanie")
                continue

            html = generate_order_html(
                order_data=data['order'],
                items=data['items']
            )

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(
                f"Wygenerowano HTML dla zamówienia {normalized_order_number}")

        except Exception as e:
            logger.error(
                f"Błąd podczas przetwarzania pliku {filename}: {str(e)}")


def process_todays_orders(db_manager, printed_orders):
    """
    Przetwarza zamówienia z dzisiejszego dnia, generując pliki JSON i HTML dla nowych zamówień.

    Args:
        db_manager: Instancja DatabaseManager
        printed_orders: Zbiór już wydrukowanych zamówień
    """
    try:
        # Pobierz dzisiejsze zamówienia
        today_orders = get_todays_orders(db_manager.connection)
        # print(today_orders)
        # return False
        # KOD_KRESKOWY

        logger.info(
            f"Znaleziono {len(today_orders)} zamówień z dzisiejszego dnia")

        if not today_orders:
            logger.info(
                "Brak zamówień z dzisiejszego dnia, kończę przetwarzanie")
            return

        # Przetwórz każde zamówienie
        for order in today_orders:
            try:
                order_number = order.get('NUMER', '')
                if not order_number:
                    logger.warning("Znaleziono zamówienie bez numeru, pomijam")
                    continue

                normalized_order_number = normalize_filename(order_number)
                logger.info(
                    f"Przetwarzanie zamówienia {order_number} (znormalizowane: {normalized_order_number})")

                # Pobierz pełne dane zamówienia z pozycjami
                order_data = load_orders_from_sql(
                    db_manager.connection, order_id=order_number)
                if not order_data or len(order_data) == 0:
                    logger.warning(
                        f"Nie znaleziono danych dla zamówienia {order_number} w bazie")
                    continue

                # Ponieważ load_orders_from_sql zwraca listę zamówień, pobieramy pierwsze
                order_with_items = order_data[0]
                items = order_with_items.get('items', [])

                # Sprawdź, czy zamówienie ma jakiekolwiek pozycje
                if not items:
                    logger.warning(
                        f"Zamówienie {order_number} nie ma żadnych pozycji, tworzę puste zamówienie")
                    # Możemy tu zdecydować, czy kontynuować przetwarzanie pustego zamówienia
                    # W tym przypadku tworzymy puste zamówienie bez pozycji
                    save_order_to_json(order, [])
                    html = generate_order_html(
                        order_data=order,
                        items=[]
                    )
                    yield order_number, html
                    continue

                # Sprawdź czy dane w bazie różnią się od zapisanych w JSON
                json_file = os.path.join(
                    get_zo_json_dir(), f"{normalized_order_number}.json")
                data_changed = False

                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)

                        # Przygotuj dane z bazy do porównania
                        current_data = {
                            'order': convert_decimal_to_str(order),
                            'items': convert_decimal_to_str(items)
                        }

                        # Porównaj dane
                        if existing_data != current_data:
                            data_changed = True
                            logger.info(
                                f"Wykryto zmiany w danych zamówienia {order_number} w bazie danych")
                            logger.info(
                                f"Porównanie danych dla zamówienia {order_number}:")
                            logger.info(
                                f"Liczba pozycji w bazie: {len(current_data['items'])}")
                            logger.info(
                                f"Liczba pozycji w JSON: {len(existing_data['items'])}")

                    except Exception as e:
                        logger.error(
                            f"Błąd podczas porównywania danych dla zamówienia {order_number}: {str(e)}")
                        data_changed = True
                else:
                    data_changed = True
                    logger.info(
                        f"Nie znaleziono pliku JSON dla zamówienia {order_number}, utworzę nowy")

                # Jeśli dane się zmieniły lub nie ma pliku JSON
                if data_changed:
                    logger.info(
                        f"Generowanie nowych plików dla zamówienia {order_number} z powodu zmian w danych")
                    # Zapisz nowe dane do JSON
                    save_order_to_json(order, items)

                    # Wygeneruj nowy HTML
                    html = generate_order_html(
                        order_data=order,
                        items=items
                    )

                    yield order_number, html
                else:
                    # Sprawdź czy zamówienie nie zostało już wydrukowane
                    if normalized_order_number in printed_orders:
                        logger.info(
                            f"Zamówienie {order_number} zostało już wydrukowane i nie zmieniło się, pomijam...")
                        continue

                    # Jeśli nie zostało wydrukowane, wygeneruj HTML
                    html = generate_order_html(
                        order_data=order,
                        items=items
                    )

                    yield order_number, html

            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania zamówienia {order.get('NUMER', 'brak numeru')}: {str(e)}",
                             exc_info=True)
                continue

    except Exception as e:
        logger.error(
            f"Błąd ogólny w process_todays_orders: {str(e)}", exc_info=True)
