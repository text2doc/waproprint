import os
import configparser
import logging

def update_config(section, key, value):
    """Aktualizuje wartość w pliku konfiguracyjnym"""
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')

        if not os.path.exists(config_path):
            logging.error(f"Plik konfiguracyjny nie istnieje: {config_path}")
            return False

        config.read(config_path)

        if section not in config:
            config[section] = {}

        config[section][key] = value

        with open(config_path, 'w') as configfile:
            config.write(configfile)

        logging.info(f"Zaktualizowano konfigurację: [{section}] {key} = {value}")
        return True
    except Exception as e:
        logging.error(f"Błąd podczas aktualizacji konfiguracji: {str(e)}")
        return False
