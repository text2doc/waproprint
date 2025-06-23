#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
import configparser


logger = logging.getLogger(__name__)

# Wczytaj konfigurację
config = configparser.ConfigParser()
config.read('config.ini')


def get_zo_pdf_dir():
    """
    Pobiera ścieżkę do katalogu z plikami HTML z config.ini.

    Returns:
        str: Ścieżka do katalogu z plikami HTML
    """
    return config.get('FILES', 'zo_pdf_dir', fallback='ZO_PDF')


def get_zo_html_dir():
    """
    Pobiera ścieżkę do katalogu z plikami HTML z config.ini.

    Returns:
        str: Ścieżka do katalogu z plikami HTML
    """
    return config.get('FILES', 'zo_html_dir', fallback='ZO_HTML')


def get_zo_json_dir():
    """
    Pobiera ścieżkę do katalogu z plikami JSON z config.ini.

    Returns:
        str: Ścieżka do katalogu z plikami JSON
    """
    return config.get('FILES', 'zo_json_dir', fallback='ZO_JSON')


def get_zo_zpl_dir():
    """
    Pobiera ścieżkę do katalogu z plikami ZPL z config.ini.

    Returns:
        str: Ścieżka do katalogu z plikami ZPL
    """
    return config.get('FILES', 'zo_zpl_dir', fallback='ZO_ZPL')


def normalize_filename(filename):
    """
    Normalizuje nazwę pliku, usuwając znaki specjalne i spacje.

    Args:
        filename (str): Oryginalna nazwa pliku

    Returns:
        str: Znormalizowana nazwa pliku
    """
    # Zamień znaki specjalne i spacje na podkreślenia
    normalized = re.sub(r'[^a-zA-Z0-9]', '_', filename)
    # Usuń wielokrotne podkreślenia
    normalized = re.sub(r'_+', '_', normalized)
    # Usuń podkreślenia z początku i końca
    normalized = normalized.strip('_')
    return normalized


def get_printed_orders():
    """
    Pobiera listę już wydrukowanych zamówień z folderu ZO_HTML.

    Returns:
        set: Zbiór numerów zamówień, które zostały już wydrukowane
    """
    zo_html_dir = get_zo_html_dir()
    if not os.path.exists(zo_html_dir):
        os.makedirs(zo_html_dir)
        return set()

    printed_orders = set()
    for filename in os.listdir(zo_html_dir):
        if filename.endswith('.html'):
            # Usuń rozszerzenie .html
            normalized_name = filename[:-5]  # Usuń .html
            # Dodaj znormalizowaną nazwę do zbioru
            printed_orders.add(normalized_name)

    logger.info(
        f"Znaleziono {len(printed_orders)} wydrukowanych zamówień: {', '.join(sorted(printed_orders))}")
    return printed_orders


def save_order_html(order_number, html_content):
    """
    Zapisuje plik HTML dla zamówienia.

    Args:
        order_number (str): Numer zamówienia
        html_content (str): Zawartość pliku HTML
    """
    # Normalizuj nazwę pliku
    normalized_name = normalize_filename(order_number)
    filename = normalized_name + '.html'

    # Upewnij się, że folder ZO istnieje
    zo_html_dir = get_zo_html_dir()
    if not os.path.exists(zo_html_dir):
        os.makedirs(zo_html_dir)

    # Pełna ścieżka do pliku
    filepath = os.path.join(zo_html_dir, filename)

    # Zapisz plik
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Zapisano plik: {filepath}")

    return filepath


def get_path_order(order_number, folder='', extension='.html'):
    """
    Zapisuje plik HTML dla zamówienia.

    Args:
        order_number (str): Numer zamówienia
        html_content (str): Zawartość pliku HTML
    """
    # Normalizuj nazwę pliku
    normalized_name = normalize_filename(order_number)
    filename = normalized_name + extension

    # Upewnij się, że folder ZO istnieje
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Pełna ścieżka do pliku
    filepath = os.path.join(folder, filename)
    logger.info(f"Sciezka pliku: {filepath}")

    return filepath
