#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys

def setup_logger():
    """
    Konfiguruje centralny logger dla całej aplikacji.
    Wszystkie logi będą zapisywane do jednego pliku i wyświetlane w konsoli.
    """
    # Pobierz ścieżkę do katalogu skryptu
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Konfiguracja formatu logów
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler do pliku
    file_handler = logging.FileHandler(os.path.join(script_dir, 'app.log'), encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    # Handler do konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Konfiguracja root loggera
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, console_handler]
    )
    
    # Zwróć logger
    return logging.getLogger(__name__)

# Utwórz globalny logger
logger = setup_logger() 