from datetime import datetime
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


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
