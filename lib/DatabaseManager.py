import sys
import logging
import pyodbc
import tabulate

# from DocumentProcessor import DocumentProcessor
# from ConfigManager import ConfigManager

from lib.log_config import get_logger
from lib.DatabaseSchemaReader import DatabaseSchemaReader  # Import the new class

logger = get_logger().getLogger(__name__)

# Add a console handler to the logger
console_handler = logging.StreamHandler()
# Set to ERROR level for database errors
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


class DatabaseManager:
    """Zarządzanie połączeniem z bazą danych"""

    def __init__(self, connection_string):
        logger.info("Inicjalizacja DatabaseManager")
        logger.info(f"Oryginalny string połączenia: {connection_string}")
        # Dodajemy parametry timeout i encryption do stringu połączenia
        if 'timeout=' not in connection_string:
            connection_string += ';timeout=30'
            logger.info("Dodano parametr timeout=30")
        if 'encrypt=' not in connection_string:
            connection_string += ';encrypt=no'
            logger.info("Dodano parametr encrypt=no")
        self.connection_string = connection_string
        logger.info(f"Finalny string połączenia: {self.connection_string}")
        self.processed_documents = set()
        self.table_names = {}
        # self.verify_database_tables()
        self.database_schema = {}  # Initialize database_schema
        # self.read_database_schema()  # Read database schema on initialization
        self.connection = None
        self.cursor = None

    def read_database_schema(self):
        """Reads and stores the database schema using DatabaseSchemaReader."""
        try:
            reader = DatabaseSchemaReader(self.connection_string)
            self.database_schema = reader.get_all_tables_and_columns()
            logger.info("Database schema read successfully.")
            # Log the schema for debugging
            logger.debug(f"Database schema: {self.database_schema}")
        except Exception as e:
            logger.error(f"Error reading database schema: {e}", exc_info=True)
            # Consider re-raising the exception or handling it appropriately

    def verify_database_tables(self):
        """Sprawdza i zapisuje prawidłowe nazwy tabel w bazie danych"""
        try:
            # Check if pyodbc is installed
            try:
                import pyodbc
            except ImportError:
                print(
                    "The 'pyodbc' module is not installed. Please install it using 'pip install pyodbc'.")
                sys.exit(1)

            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Najpierw sprawdźmy strukturę tabel
            query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND (
                TABLE_NAME IN ('DOKUMENT_MAGAZYNOWY', 'KONTRAHENT', 'OPERATOR', 'AUK_PACZKA_OPERATORZY')
                OR TABLE_NAME LIKE '%DOKUMENT%' 
                OR TABLE_NAME LIKE '%KONTRAHENT%'
                OR TABLE_NAME LIKE '%OPERATOR%'
            );
            """

            cursor.execute(query)
            tables = cursor.fetchall()

            logger.info("Znalezione tabele w bazie danych:")
            for table in tables:
                table_name = table[0]
                logger.info(f"- {table_name}")

                # Sprawdzenie struktury tabeli
                cursor.execute(f"SELECT TOP 0 * FROM {table_name}")
                columns = [column[0] for column in cursor.description]
                logger.debug(
                    f"Kolumny w tabeli {table_name}: {', '.join(columns)}")

                # Przypisanie tabel na podstawie nazwy i struktury
                if table_name == 'DOKUMENT_MAGAZYNOWY':
                    self.table_names['dokumenty'] = table_name
                elif table_name == 'KONTRAHENT':
                    self.table_names['kontrahenci'] = table_name
                elif table_name == 'AUK_PACZKA_OPERATORZY':
                    self.table_names['operatorzy'] = table_name

            # Sprawdzenie czy wszystkie wymagane tabele zostały znalezione
            required_tables = ['dokumenty', 'kontrahenci', 'operatorzy']
            missing_tables = [
                t for t in required_tables if t not in self.table_names]

            if missing_tables:
                logger.error(
                    f"Nie znaleziono następujących tabel: {', '.join(missing_tables)}")
                raise Exception("Brak wymaganych tabel w bazie danych")

            logger.info("Znalezione mapowania tabel:")
            for key, value in self.table_names.items():
                logger.info(f"- {key}: {value}")

            # Utworzenie tabeli historii wydruków jeśli nie istnieje
            create_history_table = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'WaproPrintHistory')
            BEGIN
                CREATE TABLE WaproPrintHistory (
                    ID INT IDENTITY(1,1) PRIMARY KEY,
                    DOK_ID INT NOT NULL,
                    PRINT_DATE DATETIME DEFAULT GETDATE(),
                    OPERATOR_ID VARCHAR(50),
                    PRINT_STATUS VARCHAR(20)
                );
            END
            """

            cursor.execute(create_history_table)
            conn.commit()

            # Po znalezieniu tabel, sprawdźmy ich strukturę
            if 'dokumenty' in self.table_names:
                cursor.execute(
                    f"SELECT TOP 0 * FROM {self.table_names['dokumenty']}")
                self.dokument_columns = [column[0]
                                         for column in cursor.description]
                logger.info(
                    f"Kolumny tabeli {self.table_names['dokumenty']}: {', '.join(self.dokument_columns)}")

            if 'kontrahenci' in self.table_names:
                cursor.execute(
                    f"SELECT TOP 0 * FROM {self.table_names['kontrahenci']}")
                self.kontrahent_columns = [column[0]
                                           for column in cursor.description]
                logger.info(
                    f"Kolumny tabeli {self.table_names['kontrahenci']}: {', '.join(self.kontrahent_columns)}")

            if 'operatorzy' in self.table_names:
                cursor.execute(
                    f"SELECT TOP 0 * FROM {self.table_names['operatorzy']}")
                self.operator_columns = [column[0]
                                         for column in cursor.description]
                logger.info(
                    f"Kolumny tabeli {self.table_names['operatorzy']}: {', '.join(self.operator_columns)}")

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(
                f"Błąd podczas weryfikacji tabel w bazie danych: {e}", exc_info=True)
            raise

    def test_connection(self):
        """Testuje połączenie z bazą danych"""
        try:
            logger.info("Rozpoczynam test połączenia z bazą danych")
            logger.info(
                f"Próba połączenia z bazą danych: {self.connection_string}")

            # Sprawdzamy dostępne sterowniki ODBC
            drivers = [x for x in pyodbc.drivers()]
            logger.info(f"Dostępne sterowniki ODBC: {drivers}")

            # Sprawdzamy dostępne źródła danych
            dsn_list = [x for x in pyodbc.dataSources()]
            logger.info(f"Dostępne źródła danych: {dsn_list}")

            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            logger.info(
                f"Pomyślnie połączono z bazą danych. Wersja SQL Server: {row[0]}")
            conn.close()
            return True
        except pyodbc.Error as e:
            logger.error(f"Błąd połączenia z bazą danych: {e}")
            logger.error(f"String połączenia: {self.connection_string}")
            return False
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas połączenia z bazą danych: {e}", exc_info=True)
            return False

    def get_new_documents(self, allowed_users):
        """Pobiera nowe dokumenty ZO"""
        documents = []

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Tworzenie filtra użytkowników
            user_filter = ""
            if allowed_users:
                user_list = ", ".join([f"'{user}'" for user in allowed_users])
                user_filter = f"AND op.KOD IN ({user_list})"

            # Zapytanie dostosowane do struktury tabel WAPRO
            query = f"""
                SELECT 
                    d.ID_DOK_MAGAZYNOWEGO as id,
                    d.RODZAJ_DOKUMENTU as typ_dokumentu,
                    d.NUMER as numer_pelny,
                    d.ID_KONTRAHENTA as kontrahent_id,
                    k.NAZWA as nazwa_kontrahenta,
                    k.ULICA_LOKAL as adres_kontrahenta,
                    k.KOD_POCZTOWY as kod_pocztowy,
                    k.MIEJSCOWOSC as miejscowosc,
                    op.KOD as operator_id,
                    d.UWAGI as komentarz
                FROM 
                    {self.table_names['dokumenty']} d
                JOIN 
                    {self.table_names['kontrahenci']} k ON d.ID_KONTRAHENTA = k.ID_KONTRAHENTA
                JOIN 
                    {self.table_names['operatorzy']} op ON d.ID_UZYTKOWNIKA = op.ID
                WHERE 
                    d.RODZAJ_DOKUMENTU = 'ZO' 
                    AND d.DATA >= CAST(CONVERT(VARCHAR(8), GETDATE(), 112) AS INT)
                    AND d.ID_DOK_MAGAZYNOWEGO NOT IN (SELECT DOK_ID FROM WaproPrintHistory WHERE DOK_ID IS NOT NULL)
                    {user_filter}
                ORDER BY 
                    d.DATA DESC, d.NUMER DESC
            """

            # Wykonanie zapytania
            cursor.execute(query)

            # Przetworzenie wyników
            for row in cursor.fetchall():
                doc_id = row[0]

                # Pomijamy już przetworzone dokumenty
                if doc_id in self.processed_documents:
                    continue

                # Dodajemy nowy dokument
                document = {
                    'id': doc_id,
                    'type': row[1],
                    'number': row[2],
                    'customer_id': row[3],
                    'customer_name': row[4],
                    'customer_address': row[5],
                    'customer_zipcode': row[6],
                    'customer_city': row[7],
                    'operator_id': row[8],
                    'comment': row[9] if row[9] else ''
                }

                documents.append(document)

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania nowych dokumentów: {e}", exc_info=True)

        return documents

    def get_document_items(self, document_id):
        """Pobiera pozycje dokumentu"""
        items = []

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Zapytanie pobierające pozycje dokumentu
            query = """
                SELECT 
                    p.ID_TOWARU,
                    t.NAZWA,
                    t.KOD,
                    p.ILOSC,
                    t.JM
                FROM 
                    POZYCJA_DOKUMENTU_MAGAZYNOWEGO p
                JOIN 
                    TOWAR t ON p.ID_TOWARU = t.ID_TOWARU
                WHERE 
                    p.ID_DOKUMENTU = ?
                ORDER BY 
                    p.ID_POZYCJI
            """

            # Wykonanie zapytania
            cursor.execute(query, (document_id,))

            # Przetworzenie wyników
            for row in cursor.fetchall():
                item = {
                    'product_id': row[0],
                    'product_name': row[1],
                    'product_symbol': row[2],
                    'quantity': row[3],
                    'unit': row[4]
                }

                items.append(item)

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania pozycji dokumentu {document_id}: {e}", exc_info=True)

        return items

    def update_print_history(self, document_id):
        """Aktualizuje historię wydruków"""
        if document_id is None:
            return True  # Pomijamy aktualizację jeśli nie ma ID dokumentu

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Dodanie wpisu do tabeli historii z poprawnym konwertowaniem daty
            cursor.execute("""
                INSERT INTO WaproPrintHistory (DOK_ID, PRINT_DATE, OPERATOR_ID, PRINT_STATUS)
                VALUES (?, CONVERT(DATETIME, GETDATE(), 120), ?, 'PRINTED')
            """, (document_id, 'SYSTEM'))

            conn.commit()
            cursor.close()
            conn.close()

            # Dodanie dokumentu do listy przetworzonych
            self.processed_documents.add(document_id)

            return True

        except Exception as e:
            logger.error(
                f"Błąd podczas aktualizacji historii wydruku dla dokumentu {document_id}: {e}", exc_info=True)
            return False

    def execute_query(self, query, params=None):
        """Wykonuje zapytanie SQL z opcjonalnymi parametrami"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Jeśli zapytanie zwraca wyniki, zwracamy je
            if query.strip().upper().startswith('SELECT'):
                columns = [column[0] for column in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
            else:
                # Dla zapytań modyfikujących dane (INSERT, UPDATE, DELETE)
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Błąd podczas wykonywania zapytania: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def connect(self):
        """
        Establishes a connection to the database.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            self.connection = pyodbc.connect(self.connection_string)
            self.cursor = self.connection.cursor()
            logger.info("Database schema read successfully.")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z bazą danych: {str(e)}")
            return False

    def close(self):
        """
        Closes the database connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("Połączenie z bazą danych zostało zamknięte.")

    def fetch_all(self, query, params=None):
        """
        Executes a SELECT query and returns all results.  Handles missing columns.

        Args:
            query: The SQL query string.
            params:  Optional parameters for the query.

        Returns:
            A list of pyodbc.Row objects.  Missing columns will be represented
            as None in the Row objects.
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()  # Return Row objects
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            # Keep original error message
            logger.error(f"Error executing query: {sqlstate}")
            return None

    def execute_non_query(self, query, params=None):
        """
        Executes an INSERT, UPDATE, or DELETE query.

        Args:
            query: The SQL query string.
            params: Optional parameters for the query.
        Returns:
            The number of rows affected.  Returns -1 on error.
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.rowcount
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            logger.error(f"Error executing non-query: {sqlstate}")
            self.connection.rollback()
            return -1
