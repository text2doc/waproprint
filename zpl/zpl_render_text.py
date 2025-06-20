#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_render_text.py

"""
Funkcje do renderowania tekstu w formacie ZPL
"""


def render_text_block(text, x, y, font_types, font_type='normal', width=0, alignment='L', clean_text_func=None):
    """
    Generuje kod ZPL dla bloku tekstu

    Args:
        text (str): Tekst do wyświetlenia
        x (int): Pozycja X
        y (int): Pozycja Y
        font_types (dict): Słownik z definicjami czcionek
        font_type (str): Typ czcionki (header, subheader, normal, small)
        width (int): Szerokość pola tekstowego (0 = automatyczna)
        alignment (str): Wyrównanie tekstu (L, C, R)
        clean_text_func (callable): Funkcja do czyszczenia tekstu

    Returns:
        tuple: Wygenerowany kod ZPL i nowa pozycja Y
    """
    if not text or text.strip() == "":
        return "", y

    zpl = []
    if clean_text_func:
        text = clean_text_func(text)
    else:
        text = text.strip()

    # Pobierz parametry czcionki
    font = font_types.get(font_type, font_types['normal'])
    font_name = font['name']
    font_width = font['width']
    font_height = font['height']

    # Ustaw szerokość pola tekstowego
    if width == 0 or width < font_width * 2:
        width = 500  # Domyślna szerokość pola (przybliżona)

    # Ustaw wyrównanie w ZPL
    align_value = {'L': 0, 'C': 1, 'R': 2}.get(alignment, 0)

    # Podziel tekst na linie
    lines = text.split('\n')

    # Renderuj każdą linię
    for i, line in enumerate(lines):
        if line.strip():
            # Użyj Field Block (^FB) dla zawijania tekstu
            line_y = y + (i * (font_height + 5))
            zpl.append(
                f"^FO{x},{line_y}^A{font_name}N,{font_width},{font_height}^FB{width},1,0,{align_value}^FD{line}^FS")

    # Oblicz nową pozycję Y
    new_y = y + (len(lines) * (font_height + 5))

    # Zwróć kod ZPL i nową pozycję Y
    return "\n".join(zpl), new_y


def render_multiline_text(text, x, y, font_types, font_type='normal', width=0, alignment='L', clean_text_func=None):
    """
    Generuje kod ZPL dla wieloliniowego bloku tekstu z zawijaniem słów

    Args:
        text (str): Tekst do wyświetlenia
        x (int): Pozycja X
        y (int): Pozycja Y
        font_types (dict): Słownik z definicjami czcionek
        font_type (str): Typ czcionki (header, subheader, normal, small)
        width (int): Szerokość pola tekstowego (0 = automatyczna)
        alignment (str): Wyrównanie tekstu (L, C, R)
        clean_text_func (callable): Funkcja do czyszczenia tekstu

    Returns:
        tuple: Wygenerowany kod ZPL i nowa pozycja Y
    """
    if not text or text.strip() == "":
        return "", y

    zpl = []
    if clean_text_func:
        text = clean_text_func(text)
    else:
        text = text.strip()

    # Pobierz parametry czcionki
    font = font_types.get(font_type, font_types['normal'])
    font_name = font['name']
    font_width = font['width']
    font_height = font['height']

    # Ustaw szerokość pola tekstowego
    if width == 0 or width < font_width * 2:
        width = 500  # Domyślna szerokość pola (przybliżona)

    # Ustaw wyrównanie w ZPL
    align_value = {'L': 0, 'C': 1, 'R': 2}.get(alignment, 0)

    # Użyj Field Block (^FB) z zawijaniem linii automatycznie
    # Parametry: szerokość, maksymalna liczba linii, dodatkowy odstęp między liniami, wyrównanie
    # Dla zawijania tekstu używamy większej liczby linii (np. 10)
    zpl.append(f"^FO{x},{y}^A{font_name}N,{font_width},{font_height}^FB{width},10,0,{align_value}^FD{text}^FS")

    # Szacujemy wysokość na podstawie liczby znaków i szerokości
    chars_per_line = width // (font_width * 0.6)  # Przybliżona liczba znaków w linii
    if chars_per_line <= 0:
        chars_per_line = 1

    estimated_lines = (len(text) / chars_per_line) + text.count('\n')
    new_y = y + int(estimated_lines * (font_height + 5))

    # Zwróć kod ZPL i nową pozycję Y
    return "\n".join(zpl), new_y


def render_centered_text(text, y, width, font_types, font_type='normal', clean_text_func=None):
    """
    Generuje kod ZPL dla wycentrowanego tekstu

    Args:
        text (str): Tekst do wyświetlenia
        y (int): Pozycja Y
        width (int): Szerokość etykiety
        font_types (dict): Słownik z definicjami czcionek
        font_type (str): Typ czcionki (header, subheader, normal, small)
        clean_text_func (callable): Funkcja do czyszczenia tekstu

    Returns:
        tuple: Wygenerowany kod ZPL i nowa pozycja Y
    """
    # Margines boczny
    margin = int(width * 0.1)

    # Szerokość obszaru tekstu
    text_width = width - 2 * margin

    # Renderuj tekst z wyrównaniem do środka
    return render_text_block(
        text, margin, y, font_types, font_type,
        width=text_width, alignment='C', clean_text_func=clean_text_func
    )