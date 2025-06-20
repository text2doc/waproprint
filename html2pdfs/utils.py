#!/usr/bin/env python
# -*- coding: utf-8 -*-
# html2pdfs/utils.py

"""
Moduł zawierający funkcje pomocnicze dla html2pdfs
"""

import os
import sys
import tempfile
import shutil
import random
import string
import time
import logging

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def find_wkhtmltopdf_path():
    """
    Znajduje ścieżkę do wkhtmltopdf na systemie.

    Returns:
        str: Ścieżka do wkhtmltopdf lub None jeśli nie znaleziono
    """
    # Typowe lokalizacje instalacji wkhtmltopdf na Windows
    possible_paths = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\wkhtmltopdf\bin\wkhtmltopdf.exe",
    ]

    # Sprawdź typowe lokalizacje na Windows
    if sys.platform.startswith('win'):
        for path in possible_paths:
            if os.path.isfile(path):
                return path

    # Sprawdź w PATH
    wkhtmltopdf_in_path = shutil.which("wkhtmltopdf")
    if wkhtmltopdf_in_path:
        return wkhtmltopdf_in_path

    # Dodatkowa próba w aktualnym katalogu i podfolderach
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(current_dir):
        if "wkhtmltopdf.exe" in files:
            return os.path.join(root, "wkhtmltopdf.exe")
        elif "wkhtmltopdf" in files:
            return os.path.join(root, "wkhtmltopdf")

    return None


def generate_temp_filename(prefix="output", suffix=".pdf", directory=None):
    """
    Generuje unikalną nazwę pliku w katalogu tymczasowym.

    Args:
        prefix (str): Prefiks nazwy pliku
        suffix (str): Rozszerzenie pliku
        directory (str): Katalog, w którym zostanie utworzony plik (domyślnie: temp)

    Returns:
        str: Ścieżka do wygenerowanego pliku tymczasowego
    """
    if directory is None:
        directory = tempfile.gettempdir()

    # Upewnij się, że katalog istnieje
    os.makedirs(directory, exist_ok=True)

    # Generuj losową nazwę pliku
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    timestamp = int(time.time())
    filename = f"{prefix}_{timestamp}_{random_part}{suffix}"

    return os.path.join(directory, filename)


def ensure_directory_exists(filepath):
    """
    Upewnia się, że katalog docelowy istnieje.

    Args:
        filepath (str): Ścieżka do pliku

    Returns:
        bool: True jeśli katalog istnieje lub został utworzony, False w przeciwnym razie
    """
    directory = os.path.dirname(os.path.abspath(filepath))
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Utworzono katalog: {directory}")
        except Exception as e:
            logger.warning(f"Nie można utworzyć katalogu {directory}: {e}")
            return False
    return True


def pdf_to_final_location(temp_pdf, final_pdf):
    """
    Kopiuje plik PDF z lokalizacji tymczasowej do docelowej.

    Args:
        temp_pdf (str): Ścieżka do tymczasowego pliku PDF
        final_pdf (str): Ścieżka docelowa pliku PDF

    Returns:
        str: Ścieżka do skopiowanego pliku PDF
    """
    try:
        # Upewnij się, że katalog docelowy istnieje
        ensure_directory_exists(final_pdf)

        # Kopiuj plik
        shutil.copy2(temp_pdf, final_pdf)
        logger.info(f"Skopiowano PDF z {temp_pdf} do {final_pdf}")

        # Sprawdź, czy kopiowanie się powiodło
        if os.path.exists(final_pdf) and os.path.getsize(final_pdf) > 0:
            return final_pdf
        else:
            logger.error(f"Nie udało się skopiować pliku do {final_pdf}")
            return temp_pdf

    except Exception as e:
        logger.error(f"Błąd podczas kopiowania pliku: {e}")
        logger.info(f"Pozostawiam plik w lokalizacji tymczasowej: {temp_pdf}")
        return temp_pdf