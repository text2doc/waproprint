import os
import configparser
import logging


def load_config():
    """Wczytuje konfigurację z pliku config.ini"""
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        logging.info(f"Wczytywanie konfiguracji z: {config_path}")

        if not os.path.exists(config_path):
            logging.error(f"Plik konfiguracyjny nie istnieje: {config_path}")
            return None

        config.read(config_path)
        logging.info("Konfiguracja wczytana pomyślnie")
        return config
    except Exception as e:
        logging.error(f"Błąd podczas wczytywania konfiguracji: {str(e)}")
        return None
