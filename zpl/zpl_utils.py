#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_utils.py

"""
Funkcje pomocnicze dla systemu drukowania ZPL
"""

import os
import sys
import subprocess
import logging

# Próba importu win32print dla drukowania w systemie Windows
try:
    import win32print

    WINDOWS_PRINTING = True
except ImportError:
    WINDOWS_PRINTING = False


def get_available_printers():
    """
    Pobiera listę dostępnych drukarek w systemie.

    Returns:
        list: Lista nazw drukarek
    """
    if WINDOWS_PRINTING:
        try:
            # Pobierz listę drukarek za pomocą win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            return [printer[2] for printer in printers]
        except Exception as e:
            logging.error(f"Błąd podczas pobierania listy drukarek: {e}")

    # Alternatywna metoda dla systemów bez win32print
    try:
        if sys.platform == 'win32':
            # Windows - użycie wmic
            result = subprocess.run(
                'wmic printer get name', shell=True, capture_output=True, text=True, check=True)
            # Przetworzenie listy drukarek
            drukarki = [line.strip() for line in result.stdout.split(
                '\n') if line.strip() and line.strip() != 'Name']
            return drukarki
        else:
            # Linux/Mac - użycie lpstat
            result = subprocess.run(
                'lpstat -a', shell=True, capture_output=True, text=True, check=True)
            # Przetworzenie listy drukarek
            drukarki = [line.split()[0]
                        for line in result.stdout.split('\n') if line.strip()]
            return drukarki
    except Exception as e:
        logging.error(f"Błąd podczas pobierania listy drukarek: {e}")
        return []


def get_default_printer():
    """
    Zwraca nazwę domyślnej drukarki w systemie.

    Returns:
        str: Nazwa domyślnej drukarki lub None
    """
    try:
        if WINDOWS_PRINTING:
            return win32print.GetDefaultPrinter()
        elif sys.platform == 'win32':
            # Windows bez win32print
            result = subprocess.run('wmic printer where default=TRUE get name',
                                    shell=True, capture_output=True, text=True, check=True)
            lines = [line.strip() for line in result.stdout.split(
                '\n') if line.strip() and line.strip() != 'Name']
            if lines:
                return lines[0]
        else:
            # Linux/Mac
            result = subprocess.run(
                'lpstat -d', shell=True, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            if 'system default destination:' in output:
                return output.split('system default destination:')[1].strip()
    except Exception as e:
        logging.error(f"Błąd podczas pobierania domyślnej drukarki: {e}")

    return None


def detect_zebra_printers():
    """
    Wykrywa drukarki Zebra wśród dostępnych drukarek.

    Returns:
        list: Lista nazw drukarek Zebra
    """
    all_printers = get_available_printers()

    # Filtruj drukarki Zebra (na podstawie typowych nazw)
    zebra_keywords = ['zebra', 'zdesigner', 'zt',
                      'zd', 'gk', 'gc', 'zp', 'tlp', 'lp']

    # Filtruj po nazwach
    zebra_printers = [printer for printer in all_printers
                      if any(keyword in printer.lower() for keyword in zebra_keywords)]

    return zebra_printers


def is_zebra_printer(printer_name):
    """
    Sprawdza, czy dana drukarka jest drukarką Zebra.

    Args:
        printer_name (str): Nazwa drukarki

    Returns:
        bool: True jeśli drukarka jest drukarką Zebra, False w przeciwnym wypadku
    """
    if not printer_name:
        return False

    # Typowe nazwy drukarek Zebra
    zebra_keywords = ['zebra', 'zdesigner', 'zt',
                      'zd', 'gk', 'gc', 'zp', 'tlp', 'lp']

    # Sprawdź, czy nazwa drukarki zawiera jakiekolwiek słowo kluczowe
    return any(keyword in printer_name.lower() for keyword in zebra_keywords)


def get_printer_info(printer_name):
    """
    Pobiera informacje o drukarce.

    Args:
        printer_name (str): Nazwa drukarki

    Returns:
        dict: Informacje o drukarce
    """
    printer_info = {
        'name': printer_name,
        'is_zebra': is_zebra_printer(printer_name),
        'status': 'unknown'
    }

    if WINDOWS_PRINTING and printer_name:
        try:
            # Pobierz informacje o drukarce z win32print
            h_printer = win32print.OpenPrinter(printer_name)
            printer_defaults = {"DesiredAccess": win32print.PRINTER_ACCESS_USE}
            level = 2  # Poziom szczegółowości informacji
            printer_info.update(win32print.GetPrinter(h_printer, level))
            win32print.ClosePrinter(h_printer)

            # Dodaj status
            if 'Status' in printer_info:
                status_code = printer_info['Status']

                if status_code == 0:
                    printer_info['status'] = 'ready'
                elif status_code & win32print.PRINTER_STATUS_PAUSED:
                    printer_info['status'] = 'paused'
                elif status_code & win32print.PRINTER_STATUS_ERROR:
                    printer_info['status'] = 'error'
                elif status_code & win32print.PRINTER_STATUS_OFFLINE:
                    printer_info['status'] = 'offline'
        except Exception as e:
            logging.error(
                f"Błąd podczas pobierania informacji o drukarce: {e}")

    return printer_info


def clean_filename(filename):
    """
    Czyści nazwę pliku, usuwając niedozwolone znaki.

    Args:
        filename (str): Nazwa pliku do wyczyszczenia

    Returns:
        str: Wyczyszczona nazwa pliku
    """
    if not filename:
        return ""

    # Usuń niedozwolone znaki w nazwach plików
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    clean_name = filename

    for char in invalid_chars:
        clean_name = clean_name.replace(char, '_')

    # Usuń spacje początkowe i końcowe
    clean_name = clean_name.strip()

    return clean_name
