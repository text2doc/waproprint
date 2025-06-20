import time
import win32print
import win32api
import pythoncom

from lib.DocumentProcessor import DocumentProcessor
from lib.ConfigManager import ConfigManager
from lib.DatabaseManager import DatabaseManager
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)

class MonitorService:
    """Główna klasa usługi monitorującej"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = None
        self.document_processor = None
        self.check_interval = None
        self.allowed_users = None
        self.running = False
        self.initialize()

    def initialize(self):
        """Inicjalizacja usługi"""
        connection_string = self.config_manager.get_connection_string()
        self.db_manager = DatabaseManager(connection_string)
        
        printer_name = self.config_manager.get_thermal_printer_name()
        temp_folder = self.config_manager.get_temp_folder()
        self.document_processor = DocumentProcessor(self.db_manager, printer_name, temp_folder)
        
        self.check_interval = self.config_manager.get_check_interval()
        self.allowed_users = self.config_manager.get_allowed_users()

    def start(self):
        """Uruchamia usługę monitorowania"""
        if not self.db_manager.test_connection():
            logger.error("Nie udało się połączyć z bazą danych. Usługa nie zostanie uruchomiona.")
            return False
        
        self.log_startup_info()
        self.db_manager.update_print_history(None)
        self.running = True
        
        try:
            self.run_monitoring_loop()
        except KeyboardInterrupt:
            logger.info("Otrzymano sygnał przerwania. Zatrzymywanie usługi...")
            self.stop()
        
        logger.info("Usługa została zatrzymana")
        return True

    def log_startup_info(self):
        """Loguje informacje o uruchomieniu usługi"""
        logger.info(f"Uruchamianie usługi monitorowania bazy danych")
        logger.info(f"Interwał sprawdzania: {self.check_interval} sekund")
        logger.info(f"Drukarka: {self.config_manager.get_thermal_printer_name()}")
        logger.info(f"Folder tymczasowy: {self.config_manager.get_temp_folder()}")
        
        if self.allowed_users:
            logger.info(f"Dozwoleni użytkownicy: {', '.join(self.allowed_users)}")

    def run_monitoring_loop(self):
        """Główna pętla monitorowania"""
        while self.running:
            self.check_for_new_documents()
            time.sleep(self.check_interval)

    def stop(self):
        """Zatrzymuje usługę monitorowania"""
        self.running = False

    def check_for_new_documents(self):
        """Sprawdza nowe dokumenty w bazie danych"""
        try:
            documents = self.db_manager.get_new_documents(self.allowed_users)
            
            if documents:
                logger.info(f"Znaleziono {len(documents)} nowych dokumentów")
                
                for document in documents:
                    self.document_processor.process_document(document)
                    
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania nowych dokumentów: {e}")

if __name__ == "__main__":
    monitor_service = MonitorService()
    monitor_service.start()