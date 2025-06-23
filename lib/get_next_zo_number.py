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
        logger.error(
            f"Błąd podczas pobierania następnego numeru dokumentu: {e}")
        return None
