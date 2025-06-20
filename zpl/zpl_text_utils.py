#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_text_utils.py

"""
Funkcje pomocnicze do przetwarzania tekstu dla formatu ZPL
"""

import re


def clean_text(text):
    """
    Czyści tekst do wydruku w ZPL, usuwając problematyczne znaki

    Args:
        text (str): Tekst do wyczyszczenia

    Returns:
        str: Wyczyszczony tekst
    """
    if text is None:
        return ""

    # Usuń znaki specjalne ZPL
    text = text.replace('^', '\\^').replace('~', '\\~')

    # Zastąp wielokrotne białe znaki pojedynczą spacją
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def wrap_text(text, max_width, char_width=10):
    """
    Dzieli tekst na linie o określonej maksymalnej szerokości

    Args:
        text (str): Tekst do podzielenia
        max_width (int): Maksymalna szerokość linii w punktach
        char_width (int): Szacowana szerokość jednego znaku w punktach

    Returns:
        list: Lista linii tekstu
    """
    if not text:
        return []

    # Oblicz maksymalną liczbę znaków w linii
    max_chars = max(1, int(max_width / char_width))

    # Podziel tekst na słowa
    words = text.split()

    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + (1 if current_length > 0 else 0) <= max_chars:
            # Dodaj słowo do bieżącej linii
            current_line.append(word)
            current_length += len(word) + (1 if current_length > 0 else 0)
        else:
            # Zapisz bieżącą linię i rozpocznij nową
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    # Dodaj ostatnią linię
    if current_line:
        lines.append(' '.join(current_line))

    return lines


def estimate_text_width(text, char_width=10):
    """
    Szacuje szerokość tekstu w punktach

    Args:
        text (str): Tekst do oszacowania
        char_width (int): Szacowana szerokość jednego znaku w punktach

    Returns:
        int: Szacowana szerokość tekstu w punktach
    """
    if not text:
        return 0

    return len(text) * char_width