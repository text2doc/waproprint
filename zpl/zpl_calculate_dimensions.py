#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_calculate_dimensions.py

"""
Funkcje do obliczania wymiarów elementów HTML dla formatu ZPL
"""

from bs4 import NavigableString, Tag


def calculate_element_dimensions(soup, dpi, margin_dots, font_types):
    """
    Oblicza przybliżone wymiary dokumentu HTML w jednostkach ZPL

    Args:
        soup (BeautifulSoup): Sparsowany dokument HTML
        dpi (int): Rozdzielczość w DPI
        margin_dots (int): Margines w punktach
        font_types (dict): Słownik z definicjami czcionek

    Returns:
        int: Szacowana wysokość dokumentu w punktach
    """
    total_height = margin_dots  # Rozpocznij od górnego marginesu

    # Funkcja rekurencyjna do obliczania wysokości
    def calculate_height(element, level=0):
        nonlocal total_height

        # Pomiń elementy style, script, itp.
        if element.name in ['style', 'script', 'meta', 'link', 'head']:
            return

        # Dla tekstu
        if isinstance(element, NavigableString) and element.strip():
            lines = element.strip().count('\n') + 1
            text_height = font_types['normal']['height'] * lines
            total_height += text_height
            return

        # Dla elementów blokowych
        if element.name in ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Dodaj margines przed elementem blokowym
            if level > 0:  # Nie dodawaj dla pierwszego poziomu
                # Niewielki odstęp między blokami
                total_height += int(0.05 * dpi)

            # Sprawdź, czy element ma tekst lub elementy inline
            has_content = False
            if element.text.strip():
                has_content = True
                if element.name.startswith('h'):
                    # Nagłówki są wyższe
                    heading_level = int(element.name[1])
                    font_size = max(20, 50 - (heading_level * 5))
                    total_height += font_size + 5
                else:
                    # Standardowa wysokość dla p i div
                    lines = len(element.get_text().strip().split('\n'))
                    total_height += font_types['normal']['height'] * lines

            # Dodaj wysokość dla marginesu po elemencie
            if has_content:
                total_height += int(0.05 * dpi)

        # Dla tabel
        elif element.name == 'table':
            rows = element.find_all('tr')
            for row in rows:
                # Wysokość wiersza tabeli
                # Dodajemy padding
                row_height = font_types['table_cell']['height'] + 10

                # Sprawdź, czy komórki mają wiele linii tekstu
                cells = row.find_all(['td', 'th'])
                max_lines = 1
                for cell in cells:
                    cell_text = cell.get_text().strip()
                    cell_lines = cell_text.count('\n') + 1
                    if '<br' in str(cell):
                        cell_lines += str(cell).count('<br')
                    max_lines = max(max_lines, cell_lines)

                row_height *= max_lines  # Zwiększ wysokość wiersza dla wielu linii
                total_height += row_height

            # Dodaj margines po tabeli
            total_height += int(0.1 * dpi)

        # Rekurencyjnie przetwarzaj dzieci
        if hasattr(element, 'children'):
            for child in element.children:
                if isinstance(child, (Tag, NavigableString)):
                    calculate_height(child, level + 1)

    # Rozpocznij obliczanie od body
    body = soup.find('body')
    if body:
        calculate_height(body)
    else:
        calculate_height(soup)

    # Dodaj dolny margines
    total_height += margin_dots

    return total_height
