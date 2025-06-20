from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


def get_all_tables(db_manager):
    """Pobiera wszystkie nazwy tabel z bazy danych."""
    try:
        query = """
        SELECT table_name
        FROM INFORMATION_SCHEMA.TABLES
        WHERE table_type = 'BASE TABLE'
        """
        result = db_manager.execute_query(query)
        tables = [row['table_name'] for row in result]
        return tables
    except Exception as e:
        logger.error(f"Błąd podczas pobierania nazw tabel: {e}")
        return []