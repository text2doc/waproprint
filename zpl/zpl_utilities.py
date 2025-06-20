#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_utilities.py

"""
Dodatkowe funkcje pomocnicze dla konwersji HTML do ZPL
"""

import os
import sys
import tempfile
import logging
import re

# Mapowanie kodów ZPL na szerokości drukarek (liczba kropek w linii)
PRINTER_WIDTH_MAPPING = {
    203: {  # 203 DPI
        2: 384,  # 2 cale
        3: 576,  # 3 cale
        4: 812,  # 4 cale
    },
    300: {  # 300 DPI
        2: 600,  # 2 cale
        3: 900,  # 3 cale
        4: 1200,  # 4 cale
    },
    600: {  # 600 DPI
        2: 1200,  # 2 cale
        3: 1800,  # 3 cale
        4: 2400,  # 4 cale
    }
}


def dots_to_inches(dots, dpi):
    """
    Konwertuje punkty (dots) na cale

    Args:
        dots (int): Liczba punktów
        dpi (int): Rozdzielczość w DPI

    Returns:
        float: Liczba cali
    """
    return dots / dpi


def inches_to_dots(inches, dpi):
    """
    Konwertuje cale na punkty (dots)

    Args:
        inches (float): Liczba cali
        dpi (int): Rozdzielczość w DPI

    Returns:
        int: Liczba punktów
    """
    return int(inches * dpi)


def mm_to_dots(mm, dpi):
    """
    Konwertuje milimetry na punkty (dots)

    Args:
        mm (float): Liczba milimetrów
        dpi (int): Rozdzielczość w DPI

    Returns:
        int: Liczba punktów
    """
    inches = mm / 25.4  # 1 cal = 25.4 mm
    return inches_to_dots(inches, dpi)


def dots_to_mm(dots, dpi):
    """
    Konwertuje punkty (dots) na milimetry

    Args:
        dots (int): Liczba punktów
        dpi (int): Rozdzielczość w DPI

    Returns:
        float: Liczba milimetrów
    """
    inches = dots_to_inches(dots, dpi)
    return inches * 25.4  # 1 cal = 25.4 mm


def estimate_label_size(html_content, dpi=203):
    """
    Szacuje rozmiar etykiety na podstawie zawartości HTML

    Args:
        html_content (str): Zawartość HTML
        dpi (int): Rozdzielczość w DPI

    Returns:
        tuple: (szerokość, wysokość) w calach
    """
    # Przybliżona liczba znaków w linii
    chars_per_line = len(max(html_content.split('\n'), key=len))

    # Przybliżona szerokość znaku w punktach (około 10 punktów na znak przy 203 DPI)
    char_width_dots = 10 * (dpi / 203)

    # Szacowana szerokość w punktach
    width_dots = chars_per_line * char_width_dots

    # Szacowana szerokość w calach (z zapasem)
    width_inches = dots_to_inches(width_dots, dpi) * 1.2

    # Zaokrąglij do najbliższej standardowej szerokości (2, 3 lub 4 cale)
    if width_inches <= 2.5:
        width_inches = 2
    elif width_inches <= 3.5:
        width_inches = 3
    else:
        width_inches = 4

    # Liczba linii
    line_count = html_content.count('\n') + 1

    # Przybliżona wysokość linii w punktach (około 30 punktów na linię przy 203 DPI)
    line_height_dots = 30 * (dpi / 203)

    # Szacowana wysokość w punktach
    height_dots = line_count * line_height_dots

    # Szacowana wysokość w calach (z zapasem)
    height_inches = dots_to_inches(height_dots, dpi) * 1.2

    return (width_inches, height_inches)


def save_zpl_to_file(zpl_data, output_file=None):
    """
    Zapisuje kod ZPL do pl