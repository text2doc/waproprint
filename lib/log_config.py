#!/usr/bin/env python
# -*- coding: utf-8 -*-
# lib/log_config.py
# !/usr/bin/env python
# -*- coding: utf-8 -*-
# lib/logger.py

"""
Moduł konfigurujący system logowania dla aplikacji.
Używa jednego pliku do logowania wszystkich komunikatów.
"""

import logging
import os
import sys

# Singleton logger - będzie zwracany przez funkcję get_logger
logger = None


def get_logger(filename=None, format=None):
    """
    Konfiguruje i zwraca moduł logging.
    Parametry filename i format są opcjonalne - domyślnie używa centralnej konfiguracji.

    Parametry:
    - filename: Opcjonalna ścieżka do pliku z logami (domyślnie 'app.log' w katalogu skryptu)
    - format: Opcjonalny format logów

    Zwraca:
    - Skonfigurowany obiekt logger
    """
    global logger

    # Jeśli logger został już skonfigurowany, zwróć go
    if logger:
        return logger

    # Pobierz ścieżkę do katalogu skryptu (dwa poziomy wyżej od lib/logger.py)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Określ nazwę pliku logów
    log_filename = filename if filename else os.path.join(
        script_dir, 'app.log')

    # Określ format logów
    log_format = format if format else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Konfiguracja formatu logów
    formatter = logging.Formatter(log_format)

    # Handler do pliku
    file_handler = logging.FileHandler(
        log_filename, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)

    # Handler do konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Konfiguracja root loggera
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[file_handler, console_handler]
    )

    # Zapisz logger jako singleton
    logger = logging

    # Dodaj informację o rozpoczęciu logowania
    logger.info("Rozpoczęto logowanie aplikacji")
    logger.info(f"Logi są zapisywane w pliku: {log_filename}")

    # Zwróć moduł logging
    return logger


# Funkcja do uzyskania ścieżki do pliku logów
def get_log_path():
    """
    Zwraca ścieżkę do pliku logów.

    Zwraca:
    - Ścieżka do pliku logów lub None, jeśli logger nie został jeszcze skonfigurowany
    """
    global logger

    if not logger:
        return None

    # Próbujemy znaleźć handler pliku
    for handler in logging.root.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename

    return None


# Funkcja do zmiany poziomu logowania
def set_log_level(level):
    """
    Zmienia poziom logowania.

    Parametry:
    - level: Poziom logowania (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    logging.root.setLevel(level)
    for handler in logging.root.handlers:
        handler.setLevel(level)

    logging.info(
        f"Zmieniono poziom logowania na: {logging.getLevelName(level)}")


# Inicjalizacja domyślnego loggera
logger = get_logger()

if __name__ == "__main__":
    # Test modułu
    logger.debug("To jest komunikat DEBUG")
    logger.info("To jest komunikat INFO")
    logger.warning("To jest komunikat WARNING")
    logger.error("To jest komunikat ERROR")
    logger.critical("To jest komunikat CRITICAL")

    print(f"Logi są zapisywane w pliku: {get_log_path()}")
