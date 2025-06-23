#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_encoding.py

"""
Funkcje do obsługi kodowania znaków w formacie ZPL
"""


def get_encoding_command(encoding):
    """
    Zwraca komendę ZPL dla wybranego kodowania

    Args:
        encoding (str): Kodowanie znaków (np. cp852, cp1250, utf8)

    Returns:
        str: Komenda ZPL dla wybranego kodowania
    """
    encoding_map = {
        'cp850': "^CI12",  # PC850 Multilingual
        'cp852': "^CI13",  # PC852 Latin 2
        'cp1250': "^CI2",  # Windows-1250
        'cp1252': "^CI8",  # Windows-1252
        'utf8': "^CI28",  # UTF-8
        'utf-8': "^CI28",  # UTF-8
        'cp437': "^CI0"  # US English
    }
    # Domyślnie CP852 dla polskich znaków
    return encoding_map.get(encoding.lower(), "^CI13")
