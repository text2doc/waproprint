#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funkcje do tworzenia i zarządzania dokumentami ZO.
"""

from datetime import datetime
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)

def get_next_zo_number(db_manager):
    """Pobiera następny dostępny numer dokumentu ZO"""
    try:
        current_year = datetime.now().year % 100  # Pobieramy ostatnie 2 cyfry roku

        query = f"""
        SELECT MAX(CAST(SUBSTRING(NUMER, 4, CHARINDEX('/', NUMER) - 4) AS INT)) as max_number
        FROM DOKUMENT_MAGAZYNOWY
        WHERE RODZAJ_DOKUMENTU = 'ZO'
        AND NUMER LIKE 'ZO %/{current_year}'
        """

        result = db_manager.execute_query(query)
        if result and result[0]['max_number'] is not None:
            next_number = result[0]['max_number'] + 1
        else:
            next_number = 1

        return f"ZO {next_number:04d}/{current_year}"

    except Exception as e:
        logger.error(f"Błąd podczas pobierania następnego numeru dokumentu: {e}")
        return None

def create_new_zo(db_manager, next_number):
    """Tworzy nowy dokument ZO w bazie danych"""
    try:
        # Konwertujemy datę na format YYYYMMDD (int)
        current_date = int(datetime.now().strftime('%Y%m%d'))

        # Pobierz ID operatora (domyślnie 1 dla administratora)
        query = """
        INSERT INTO DOKUMENT_MAGAZYNOWY (
            NUMER, DATA, RODZAJ_DOKUMENTU, ID_UZYTKOWNIKA,
            WARTOSC_NETTO, WARTOSC_BRUTTO, FLAGA_STANU
        ) VALUES (
            ?, ?, 'ZO', 1,
            0, 0, 0
        )
        """

        db_manager.execute_query(query, (next_number, current_date))
        logger.info(f"Utworzono nowy dokument ZO: {next_number}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia nowego dokumentu ZO: {e}")
        return False
