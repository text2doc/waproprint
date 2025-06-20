from lib.log_config import get_logger
from tabulate import tabulate

logger = get_logger().getLogger(__name__)


def print_tables(tables):
    """Wyświetla nazwy tabel w formie tabeli."""
    if not tables:
        print("\nNie znaleziono żadnych tabel w bazie danych.")
        return

    # Przygotowanie danych do wyświetlenia
    table_data = [[table] for table in tables]

    # Nagłówki kolumn
    headers = ["Nazwa tabeli"]

    # Wyświetlenie tabeli
    print("\nTabele w bazie danych:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))