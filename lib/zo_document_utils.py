#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funkcje pomocnicze do obsługi dokumentów ZO.
"""

from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


def get_zo_documents(db_manager):
    """Pobiera dokumenty ZO z bazy danych"""
    try:
        query = """
        SELECT 
            d.NUMER as numer_dokumentu,
            d.DATA as data_dokumentu,
            k.NAZWA as kontrahent,
            d.WARTOSC_NETTO as wartosc_netto,
            d.WARTOSC_BRUTTO as wartosc_brutto,
            d.UWAGI as uwagi,
            d.ODEBRAL as odebral
        FROM DOKUMENT_MAGAZYNOWY d
        LEFT JOIN KONTRAHENT k ON d.ID_KONTRAHENTA = k.ID_KONTRAHENTA
        WHERE d.RODZAJ_DOKUMENTU = 'ZO'
        ORDER BY d.DATA DESC, d.NUMER DESC
        """

        return db_manager.execute_query(query)

    except Exception as e:
        logger.error(f"Błąd podczas pobierania dokumentów: {e}")
        return []
