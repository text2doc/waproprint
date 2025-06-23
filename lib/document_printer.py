#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funkcja do drukowania dokumentów PDF.
"""

import os
import subprocess
import platform
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


def print_document(pdf_path, printer_name=None):
    """
    Drukuje dokument PDF na wskazanej drukarce.

    Args:
        pdf_path (str): Ścieżka do pliku PDF
        printer_name (str, optional): Nazwa drukarki. Jeśli None, użyta zostanie domyślna drukarka.

    Returns:
        bool: True jeśli drukowanie się powiodło, False w przeciwnym razie
    """
    try:
        if not os.path.exists(pdf_path):
            logger.error(f"Plik PDF nie istnieje: {pdf_path}")
            return False

        system = platform.system()

        if system == "Windows":
            # Drukowanie na Windows
            if printer_name:
                cmd = ['SumatraPDF.exe', '-print-to', printer_name, pdf_path]
            else:
                cmd = ['SumatraPDF.exe', '-print-to-default', pdf_path]

            # Alternatywnie można użyć Adobe Reader:
            # cmd = ['AcroRd32.exe', '/t', pdf_path, printer_name] if printer_name else ['AcroRd32.exe', '/t', pdf_path]

        elif system == "Linux":
            # Drukowanie na Linux
            if printer_name:
                cmd = ['lpr', '-P', printer_name, pdf_path]
            else:
                cmd = ['lpr', pdf_path]

        elif system == "Darwin":  # macOS
            # Drukowanie na macOS
            if printer_name:
                cmd = ['lpr', '-P', printer_name, pdf_path]
            else:
                cmd = ['lpr', pdf_path]

        else:
            logger.error(f"Nieobsługiwany system operacyjny: {system}")
            return False

        # Uruchomienie komendy drukowania
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            logger.error(
                f"Błąd podczas drukowania: {stderr.decode('utf-8', errors='ignore')}")
            return False

        logger.info(
            f"Dokument {pdf_path} został wysłany do drukarki {printer_name or 'domyślnej'}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas drukowania dokumentu: {e}")
        return False
