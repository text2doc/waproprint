"""
Skrypt do tworzenia dokumentu ZO na podstawie istniejącego dokumentu.
"""

import pyodbc
from lib.get_next_zo_number import get_next_zo_number

import datetime
import win32print
import win32api
import pythoncom


from datetime import datetime
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)
from lib.ConfigManager import ConfigManager
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


def create_zo_from_existing():
    """Tworzy dokument ZO na podstawie istniejącego dokumentu"""
    try:
        # Wczytanie konfiguracji
        logger.info("Wczytuję konfigurację...")
        config = ConfigManager()
        connection_string = config.get_connection_string()

        # Inicjalizacja połączenia z bazą danych
        logger.info("Inicjalizuję połączenie z bazą danych...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Sprawdzenie struktury tabeli
        logger.info("Sprawdzam strukturę tabeli DOKUMENT_MAGAZYNOWY...")
        cursor.execute("""
        SELECT 
            c.name as column_name,
            t.name as data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable
        FROM sys.columns c
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE OBJECT_NAME(c.object_id) = 'DOKUMENT_MAGAZYNOWY'
        ORDER BY c.column_id;
        """)

        columns = cursor.fetchall()
        for col in columns:
            logger.info(f"Kolumna: {col.column_name}, Typ: {col.data_type}, Nullable: {col.is_nullable}")

        # Pobierz ostatni dokument PZ lub WZ
        query = """
        SELECT TOP 1 *
        FROM DOKUMENT_MAGAZYNOWY d
        WHERE d.RODZAJ_DOKUMENTU IN ('PZ', 'WZ')
        ORDER BY d.DATA DESC
        """

        cursor.execute(query)
        source_doc = cursor.fetchone()

        if not source_doc:
            logger.error("Nie znaleziono żadnego dokumentu źródłowego (PZ/WZ)")
            return False

        logger.info(f"Znaleziono dokument źródłowy: {source_doc.NUMER}")

        # Sprawdzenie struktury tabeli DOKUMENT_MAGAZYNOWY
        logger.info("\nSprawdzam szczegółową strukturę tabeli DOKUMENT_MAGAZYNOWY...")
        cursor.execute("""
        SELECT 
            c.name as column_name,
            t.name as data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable,
            c.default_object_id,
            OBJECT_DEFINITION(c.default_object_id) as default_value
        FROM sys.columns c
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE OBJECT_NAME(c.object_id) = 'DOKUMENT_MAGAZYNOWY'
        ORDER BY c.column_id;
        """)

        doc_columns = cursor.fetchall()
        logger.info("\nStruktura tabeli DOKUMENT_MAGAZYNOWY:")
        for col in doc_columns:
            logger.info(f"Kolumna: {col.column_name}")
            logger.info(f"  Typ: {col.data_type}")
            logger.info(f"  Nullable: {col.is_nullable}")
            logger.info(f"  Max Length: {col.max_length}")
            logger.info(f"  Precision: {col.precision}")
            logger.info(f"  Scale: {col.scale}")
            if col.default_value:
                logger.info(f"  Default Value: {col.default_value}")
            logger.info("---")

        # Sprawdzenie struktury tabeli POZYCJA_DOKUMENTU_MAGAZYNOWEGO
        logger.info("\nSprawdzam szczegółową strukturę tabeli POZYCJA_DOKUMENTU_MAGAZYNOWEGO...")
        cursor.execute("""
        SELECT 
            c.name as column_name,
            t.name as data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable,
            c.default_object_id,
            OBJECT_DEFINITION(c.default_object_id) as default_value
        FROM sys.columns c
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE OBJECT_NAME(c.object_id) = 'POZYCJA_DOKUMENTU_MAGAZYNOWEGO'
        ORDER BY c.column_id;
        """)

        pos_columns = cursor.fetchall()
        logger.info("\nStruktura tabeli POZYCJA_DOKUMENTU_MAGAZYNOWEGO:")
        for col in pos_columns:
            logger.info(f"Kolumna: {col.column_name}")
            logger.info(f"  Typ: {col.data_type}")
            logger.info(f"  Nullable: {col.is_nullable}")
            logger.info(f"  Max Length: {col.max_length}")
            logger.info(f"  Precision: {col.precision}")
            logger.info(f"  Scale: {col.scale}")
            if col.default_value:
                logger.info(f"  Default Value: {col.default_value}")
            logger.info("---")

        # Generowanie nowego numeru ZO
        new_num = get_next_zo_number(cursor)
        if not new_num:
            logger.error("Nie udało się wygenerować nowego numeru dokumentu")
            return False

        # Wstawienie nowego dokumentu ZO
        current_date = int(datetime.datetime.now().strftime('%Y%m%d'))
        query = """
        INSERT INTO DOKUMENT_MAGAZYNOWY (
            RODZAJ_DOKUMENTU,
            NUMER,
            DATA,
            ID_KONTRAHENTA,
            ID_UZYTKOWNIKA,
            WARTOSC_NETTO,
            WARTOSC_BRUTTO,
            BRUTTO_NETTO,
            UWAGI,
            ID_MAGAZYNU,
            ID_TYPU,
            PRZYCHOD,
            ROZCHOD,
            TRYB_ROZCHODU,
            SEMAFOR,
            PODST_PRZYJ,
            AUTONUMER,
            WYCENA,
            FLAGA_STANU,
            DOK_ZWERYFIKOWANY,
            TRYBREJESTRACJI
        ) VALUES (
            'ZO',
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            'Netto',
            ?,
            ?,
            ?,
            CAST(? as bit),
            CAST(? as bit),
            ?,
            ?,
            ?,
            ?,
            ?,
            0,
            0,
            0
        )
        """

        cursor.execute(query, (
            new_num,
            current_date,
            source_doc.ID_KONTRAHENTA,
            source_doc.ID_UZYTKOWNIKA,
            source_doc.WARTOSC_NETTO,
            source_doc.WARTOSC_BRUTTO,
            f"Utworzone na podstawie dokumentu {source_doc.NUMER}",
            source_doc.ID_MAGAZYNU,
            source_doc.ID_TYPU,
            source_doc.PRZYCHOD,
            source_doc.ROZCHOD,
            source_doc.TRYB_ROZCHODU,
            source_doc.SEMAFOR,
            source_doc.PODST_PRZYJ,
            source_doc.AUTONUMER,
            source_doc.WYCENA
        ))

        # Pobierz ID nowego dokumentu
        cursor.execute("SELECT SCOPE_IDENTITY() as new_id")
        new_doc_id = cursor.fetchone()[0]

        # Wstawienie pozycji dokumentu
        query = """
        INSERT INTO POZYCJA_DOKUMENTU_MAGAZYNOWEGO (
            ID_DOK_MAGAZYNOWEGO,
            ID_ARTYKULU,
            ILOSC,
            CENA_NETTO,
            CENA_BRUTTO,
            TRYBREJESTRACJI
        )
        SELECT 
            CAST(? as numeric),
            ID_ARTYKULU,
            ILOSC,
            CENA_NETTO,
            CENA_BRUTTO,
            CAST(0 as numeric)
        FROM POZYCJA_DOKUMENTU_MAGAZYNOWEGO
        WHERE ID_DOK_MAGAZYNOWEGO = ?
        """

        cursor.execute(query, (new_doc_id, source_doc.ID_DOK_MAGAZYNOWEGO))

        conn.commit()
        logger.info(f"Utworzono nowy dokument ZO: {new_num}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia dokumentu ZO: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
