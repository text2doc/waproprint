import pyodbc
import logging

logger = logging.getLogger(__name__)

class DatabaseSchemaReader:
    """
    A class to read database schema information.
    """

    def __init__(self, connection_string):
        """
        Initializes the DatabaseSchemaReader with a connection string.

        Args:
            connection_string (str): The database connection string.
        """
        self.connection_string = connection_string

    def get_all_tables_and_columns(self):
        """
        Retrieves all table names and their columns from the database.

        Returns:
            dict: A dictionary where keys are table names and values are lists of column names.
        """
        tables_and_columns = {}
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            tables = [table[0] for table in cursor.fetchall()]

            for table_name in tables:
                # Get column names for each table
                cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
                columns = [column[0] for column in cursor.fetchall()]
                tables_and_columns[table_name] = columns

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error reading database schema: {e}", exc_info=True)
            raise

        return tables_and_columns