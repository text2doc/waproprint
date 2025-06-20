from datetime import date, timedelta
import logging
import sys
import os
import pdfkit  # Import pdfkit
from weasyprint import HTML, CSS #added for improved pdf generation
from weasyprint.fonts import FontConfiguration #added for font config

# Add the 'lib' directory to the Python path *explicitly*.
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(current_dir, 'lib')
sys.path.insert(0, lib_dir)

import pyodbc

class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, config):
        """
        Initializes the DatabaseManager with the provided configuration.

        Args:
            config: A dictionary containing database connection settings
                    (server, database, trusted_connection, username, password).
        """
        self.config = config
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establishes a connection to the database."""
        try:
            if self.config['trusted_connection'].lower() == 'yes':
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.config['server']};"
                    f"DATABASE={self.config['database']};"
                    f"Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.config['server']};"
                    f"DATABASE={self.config['database']};"
                    f"UID={self.config['username']};"
                    f"PWD={self.config['password']};"
                )

            self.connection = pyodbc.connect(conn_str)
            self.cursor = self.connection.cursor()
            print("Database connection established.")

        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Database connection error: {sqlstate}")
            raise

    def disconnect(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Database connection closed.")


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
            print(f"Error executing query: {sqlstate}")  # Keep original error message
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
            print(f"Error executing non-query: {sqlstate}")
            self.connection.rollback()
            return -1



import configparser

class ConfigManager:
    """Manages configuration settings from a file."""

    def __init__(self, config_file='../config.ini'):
        """
        Initializes and loads settings from the specified file.
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

    def get_database_config(self):
        """Retrieves the database configuration settings."""
        return self.config['DATABASE']

    def get_printing_config(self):
        """Retrieves the printer configuration settings."""
        return self.config['PRINTING']

    def get_users_config(self):
        """Retrieves the users configuration settings."""
        return self.config['USERS']

    def get_document_config(self):
        """Retrieves the document configuration settings."""
        return self.config['DOCUMENT']



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("../list_orders.log"),
        logging.StreamHandler()
    ]
)
from datetime import date, timedelta
import logging
import sys
import os

# Add the 'lib' directory to the Python path *explicitly*.
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(current_dir, 'lib')
sys.path.insert(0, lib_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("../list_orders.log"),
        logging.StreamHandler()
    ]
)

def get_zamowienia_data(dni):
    """
    Fetches order data, groups by order ID, and returns basic information.
    Skips empty values.
    """
    config_manager = ConfigManager()
    try:
        db_config = config_manager.get_database_config()
    except Exception as e:
        logging.exception("Error loading database configuration: %s", e)
        return None

    db_manager = DatabaseManager(db_config)

    try:
        db_manager.connect()
        query = """
            SELECT
                *
            FROM
                ZAMOWIENIE Z
            LEFT JOIN
                KONTRAHENT K ON Z.ID_KONTRAHENTA = K.ID_KONTRAHENTA
            LEFT JOIN
                POZYCJA_ZAMOWIENIA PZ ON Z.ID_ZAMOWIENIA = PZ.ID_ZAMOWIENIA
            LEFT JOIN
                ARTYKUL A ON PZ.ID_ARTYKULU = A.ID_ARTYKULU
            WHERE Z.DATA BETWEEN ? AND ?
            ORDER BY Z.ID_ZAMOWIENIA, PZ.ID_POZYCJI_ZAMOWIENIA;
        """
        today = date.today()
        today_int = int(today.strftime("%Y%m%d"))
        future_date = today + timedelta(days=dni)
        future_date_int = int(future_date.strftime("%Y%m%d"))

        params = (today_int, future_date_int)
        results = db_manager.fetch_all(query, params)

        orders = {}  # Main dictionary to hold all orders

        if results:
            for row in results:
                # --- 1. Extract Order-Level Data (Dynamically) ---
                order_id = None
                for col in row.cursor_description:
                    if 'ID_ZAMOWIENIA' in col[0].upper():
                        order_id = getattr(row, col[0])
                        break  # Found the order ID, no need to continue
                if order_id is None:
                    logging.warning("Row skipped: No order ID found.")
                    continue

                if order_id not in orders:
                    orders[order_id] = {
                        'order_data': {},  # For order-specific details
                        'contractor': {},  # For contractor details
                        'items': []       # For order items
                    }
                    # Add order details (dynamically, but with some filtering)
                    for col in row.cursor_description:
                        col_name = col[0]
                        value = getattr(row, col_name)
                        if value is not None and 'KONTRAHENT' not in col_name.upper() and 'ID_ARTYKULU' not in col_name.upper() and 'ID_POZYCJI' not in col_name.upper() :
                            orders[order_id]['order_data'][col_name] = value


                # --- 2. Extract Contractor Data (Dynamically) ---
                    for col in row.cursor_description:
                        col_name = col[0]
                        value = getattr(row, col_name)
                        if value is not None and 'KONTRAHENT' in col_name.upper():
                            orders[order_id]['contractor'][col_name] = value

                # --- 3. Extract Order Item Data (Dynamically) ---
                item = {}
                for col in row.cursor_description:
                    col_name = col[0]
                    value = getattr(row, col_name)
                    if value is not None and 'ZAMOWIENIE' not in col_name.upper() and 'KONTRAHENT' not in col_name.upper():
                        item[col_name] = value
                if item: # Append only if item has data
                    orders[order_id]['items'].append(item)

        return orders

    except Exception as e:
        logging.exception("Error fetching and structuring orders: %s", e)
        return None
    finally:
        db_manager.disconnect()

def print_basic_order_info(orders):
    """Prints basic order information, skipping empty values."""
    if not orders:
        print("No orders to print.")
        return

    for order_id, order_data in orders.items():
        print("=" * 30)
        print(f"ID Zamówienia: {order_id}")

        # Print order data
        if order_data['order_data']:
            print("-" * 20)
            print("Dane Zamówienia:")
            for key, value in order_data['order_data'].items():
                if value:  # Check if the value is not None/empty
                    print(f"  {key}: {value}")

        # Print contractor data
        if order_data['contractor']:
            print("-" * 20)
            print("Kontrahent:")
            for key, value in order_data['contractor'].items():
                if value:
                    print(f"  {key}: {value}")

        # Print items data
        if order_data['items']:
            print("-" * 20)
            print("Pozycje Zamówienia:")
            for item in order_data['items']:
                for key, value in item.items():
                    if value:
                        print(f"    {key}: {value}")
                print("  " + "-" * 18)
        print("=" * 30 + "\n")

def generate_pdf_from_html(html_content, output_filename):
    """Generates a PDF from HTML content using WeasyPrint."""
    try:
        font_config = FontConfiguration()
        HTML(string=html_content).write_pdf(output_filename, font_config=font_config)
        logging.info(f"PDF generated successfully: {output_filename}")
    except Exception as e:
        logging.exception(f"Error generating PDF: {e}")

def html_to_zpl(html_content, scale_x=2, scale_y=2):
    """Converts HTML content to ZPL, with basic scaling.  Very rudimentary!"""
    # Extremely basic HTML to ZPL conversion.  This is a placeholder
    # and needs significant improvement for real-world use.
    zpl_code = "^XA\n"  # Start ZPL

    # Remove HTML tags and scale text (very crudely)
    text = html_content.replace("<br>", "\n").replace("<h1>", "").replace("</h1>", "\n").replace("<b>", "").replace("</b>", "")
    lines = text.split("\n")

     # Add the 'lib' directory to the Python path *explicitly*.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(current_dir, 'lib')
    sys.path.insert(0, lib_dir)
    y_pos = 20
    for line in lines:
        if line.strip():  # Skip empty lines
            zpl_code += f"^FO20,{y_pos}^A0,{20*scale_y},{15*scale_x}^FD{line.strip()}^FS\n" # A0 font, normal
            y_pos += 20 * scale_y

    zpl_code += "^XZ"  # End ZPL
    return zpl_code


def generate_outputs_from_html(html_file):
    """
    Generates a PDF and ZPL output from an HTML file.

    Args:
        html_file: Path to the HTML file.
    """
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        logging.error(f"HTML file not found: {html_file}")
        return
    except Exception as e:
        logging.exception(f"Error reading HTML file: {e}")
        return

    # 1. Generate PDF
    pdf_filename = os.path.splitext(html_file)[0] + ".pdf"
    generate_pdf_from_html(html_content, pdf_filename)

    # 2. Generate ZPL (rudimentary conversion)
    zpl_filename = os.path.splitext(html_file)[0] + ".zpl"
    zpl_code = html_to_zpl(html_content) # Very basic conversion
    try:
        with open(zpl_filename, 'w', encoding='utf-8') as f:
            f.write(zpl_code)
        logging.info(f"ZPL generated successfully: {zpl_filename}")
    except Exception as e:
        logging.exception(f"Error writing ZPL file: {e}")

if __name__ == '__main__':
    # num_days = 7
    # logging.info("Script started.")
    # orders = get_zamowienia_data(num_days)

    # Example usage with a dummy HTML file
    # if orders:
        # In a real scenario, you'd generate the HTML dynamically
        # based on the 'orders' data.  For this example, we'll use
        # a static HTML file.
    generate_outputs_from_html("../zamowienie.html")
    # else:
    #     print("No orders found or an error occurred.")
