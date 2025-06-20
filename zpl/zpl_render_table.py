#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_render_table.py

"""
Funkcje do renderowania tabel HTML w formacie ZPL
"""

import re
from bs4 import Tag


def render_table(table, start_x, start_y, width_dots, font_types, render_text_func):
    """
    Generuje kod ZPL dla tabeli HTML

    Args:
        table (BeautifulSoup): Element tabeli
        start_x (int): Początkowa pozycja X
        start_y (int): Początkowa pozycja Y
        width_dots (int): Szerokość etykiety w punktach
        font_types (dict): Słownik z definicjami czcionek
        render_text_func (callable): Funkcja do renderowania tekstu

    Returns:
        tuple: Wygenerowany kod ZPL i nowa pozycja Y
    """
    zpl = []
    current_y = start_y

    # Znajdź wszystkie wiersze
    rows = table.find_all('tr')
    if not rows:
        return "", current_y

    # Znajdź wszystkie nagłówki i komórki, aby określić kolumny
    all_cells = []
    for row in rows:
        cells = row.find_all(['th', 'td'])
        all_cells.extend(cells)

    # Określ liczbę kolumn na podstawie wiersza z największą liczbą komórek
    max_columns = max(len(row.find_all(['th', 'td'])) for row in rows)

    # Oblicz szerokość kolumn
    usable_width = width_dots - 2 * start_x

    # Analizuj zawartość komórek, aby lepiej dostosować szerokości kolumn
    column_content_lengths = [0] * max_columns
    column_is_numeric = [True] * max_columns  # Zakładamy początkowo, że wszystkie kolumny są numeryczne

    for row in rows:
        cells = row.find_all(['th', 'td'])
        for i, cell in enumerate(cells):
            if i < max_columns:
                # Analizuj długość tekstu w komórce
                text = cell.get_text().strip().replace('\n', ' ')

                # Sprawdź, czy komórka ma klasę lub stylizację wskazującą na wyrównanie do prawej (np. currency)
                is_right_aligned = False
                if cell.has_attr('class') and ('currency' in cell['class'] or 'right' in cell['class']):
                    is_right_aligned = True
                elif cell.has_attr('style') and ('right' in cell['style'] or 'text-align: right' in cell['style']):
                    is_right_aligned = True

                # Sprawdź, czy tekst jest liczbą
                is_numeric = bool(re.match(r'^[\d\s.,]+$', text))

                # Jeśli kolumna zawiera nie-numeryczne wartości, zaznacz to
                if not is_numeric and not text == "":
                    column_is_numeric[i] = False

                # Jeśli w komórce jest <br>, dodaj dodatkowe miejsce
                if '<br' in str(cell):
                    text_length = len(text) * 1.5
                else:
                    text_length = len(text)
                column_content_lengths[i] = max(column_content_lengths[i], text_length)

    # Dostosuj szerokości kolumn na podstawie zawartości
    total_content_length = sum(column_content_lengths)
    if total_content_length == 0:
        # Równe szerokości, jeśli nie ma zawartości
        column_widths = [usable_width // max_columns] * max_columns
    else:
        # Proporcjonalne szerokości na podstawie zawartości
        column_widths = []
        for length in column_content_lengths:
            # Każda kolumna otrzymuje co najmniej 10% szerokości
            min_width = usable_width * 0.1 / max_columns
            # Reszta jest rozdzielana proporcjonalnie
            proportional_width = (length / total_content_length) * usable_width * 0.9
            column_width = int(min_width + proportional_width)

            # Dodatkowe sprawdzenie dla komórek z długim tekstem
            # Konwertuj znaki na przybliżoną szerokość w punktach (dots)
            char_width = font_types['table_cell']['width'] * 0.6  # Przybliżona szerokość znaku
            text_width = length * char_width

            # Jeśli tekst jest zbyt szeroki, daj tej kolumnie więcej miejsca
            if text_width > column_width:
                column_width = min(int(text_width), int(usable_width * 0.4))  # Maks 40% dostępnej szerokości

            column_widths.append(column_width)

        # Upewnij się, że suma szerokości nie przekracza dostępnej szerokości
        while sum(column_widths) > usable_width:
            # Znajdź najszerszą kolumnę i zmniejsz ją
            max_index = column_widths.index(max(column_widths))
            column_widths[max_index] -= 1

    # Przetwórz każdy wiersz tabeli
    for row_index, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])

        # Sprawdź, czy to wiersz nagłówka
        is_header = row.find_parent('thead') is not None or any(cell.name == 'th' for cell in cells)

        # Oblicz wysokość wiersza na podstawie zawartości
        row_height = font_types['table_header' if is_header else 'table_cell']['height'] + 10

        # Sprawdź, czy komórki zawierają wiele linii tekstu
        max_lines = 1
        for cell in cells:
            cell_text = cell.get_text().strip()
            cell_lines = cell_text.count('\n') + 1
            if '<br' in str(cell):
                cell_lines += str(cell).count('<br')
            max_lines = max(max_lines, cell_lines)

        # Dostosuj wysokość wiersza do liczby linii
        row_height *= max_lines

        # Narysuj tło wiersza nagłówka
        if is_header:
            zpl.append(f"^FO{start_x},{current_y}^GB{usable_width},{row_height},2^FS")

        # Rysuj komórki
        current_x = start_x
        for col_index, cell in enumerate(cells):
            if col_index >= max_columns:
                break

            # Szerokość tej komórki
            cell_width = column_widths[col_index]

            # Sprawdź, czy kolumna powinna być wyrównana do prawej (dla liczb)
            alignment = 'R' if column_is_numeric[col_index] else 'L'

            # Sprawdź indywidualne wyrównanie komórki na podstawie klas i stylów
            if cell.has_attr('class'):
                classes = cell['class'] if isinstance(cell['class'], list) else [cell['class']]
                if 'currency' in classes or 'right' in classes:
                    alignment = 'R'
                elif 'center' in classes:
                    alignment = 'C'
                elif 'left' in classes:
                    alignment = 'L'

            # Pobierz tekst z komórki
            cell_text = cell.get_text().strip()

            # Obsługa BR w komórkach - zamień na rzeczywiste znaki nowej linii
            if '<br' in str(cell):
                # Zastąp tagi <br> znakiem nowej linii
                cell_text = re.sub(r'<br\s*/*>', '\n', str(cell))
                # Usuń pozostałe tagi HTML
                cell_text = re.sub(r'<[^>]*>', '', cell_text)
                cell_text = cell_text.strip()

            # Renderuj tekst komórki
            font_type = 'table_header' if is_header else 'table_cell'
            cell_zpl, _ = render_text_func(
                cell_text,
                current_x + 5,  # Dodaj padding wewnętrzny
                current_y + 5,  # Dodaj padding wewnętrzny
                font_type=font_type,
                width=cell_width - 10,  # Odejmij padding
                alignment=alignment
            )
            zpl.append(cell_zpl)

            # Narysuj obramowanie komórki
            zpl.append(f"^FO{current_x},{current_y}^GB{cell_width},{row_height},1^FS")

            # Przesuń x dla następnej komórki
            current_x += cell_width

        # Przesuń pozycję Y dla następnego wiersza
        current_y += row_height

    # Dodaj dodatkowy odstęp po tabeli
    current_y += 20

    # Zwróć kod ZPL i nową pozycję Y
    return "\n".join(zpl), current_y


def analyze_table_structure(table):
    """
    Analizuje strukturę tabeli HTML

    Args:
        table (BeautifulSoup): Element tabeli

    Returns:
        dict: Informacje o strukturze tabeli
    """
    result = {
        'columns': 0,
        'rows': 0,
        'header_rows': 0,
        'footer_rows': 0,
        'has_complex_cells': False,
        'column_types': []
    }

    # Znajdź wszystkie wiersze
    rows = table.find_all('tr')
    result['rows'] = len(rows)

    # Określ liczbę kolumn
    result['columns'] = max([len(row.find_all(['td', 'th'])) for row in rows]) if rows else 0

    # Sprawdź wiersze nagłówka
    header_rows = table.find('thead').find_all('tr') if table.find('thead') else []
    result['header_rows'] = len(header_rows)

    # Sprawdź wiersze stopki
    footer_rows = table.find('tfoot').find_all('tr') if table.find('tfoot') else []
    result['footer_rows'] = len(footer_rows)

    # Sprawdź, czy tabela ma złożone komórki (colspan, rowspan)
    for row in rows:
        for cell in row.find_all(['td', 'th']):
            if cell.has_attr('colspan') or cell.has_attr('rowspan'):
                result['has_complex_cells'] = True
                break

    # Określ typy kolumn (tekst, liczba)
    column_is_numeric = [True] * result['columns']

    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            if i < result['columns']:
                text = cell.get_text().strip()
                # Sprawdź, czy tekst jest liczbą
                is_numeric = bool(re.match(r'^[\d\s.,]+$', text))
                if not is_numeric and text:
                    column_is_numeric[i] = False

    result['column_types'] = ['numeric' if is_num else 'text' for is_num in column_is_numeric]

    return result


def calculate_column_widths(table, usable_width, font_types):
    """
    Oblicza optymalne szerokości kolumn dla tabeli

    Args:
        table (BeautifulSoup): Element tabeli
        usable_width (int): Dostępna szerokość w punktach
        font_types (dict): Słownik z definicjami czcionek

    Returns:
        list: Lista szerokości kolumn
    """
    rows = table.find_all('tr')
    if not rows:
        return []

    # Określ liczbę kolumn
    max_columns = max([len(row.find_all(['td', 'th'])) for row in rows])

    # Analizuj zawartość komórek
    column_content_lengths = [0] * max_columns

    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            if i < max_columns:
                text = cell.get_text().strip().replace('\n', ' ')
                # Jeśli w komórce jest <br>, dodaj dodatkowe miejsce
                if '<br' in str(cell):
                    text_length = len(text) * 1.5
                else:
                    text_length = len(text)
                column_content_lengths[i] = max(column_content_lengths[i], text_length)

    # Oblicz szerokości kolumn
    total_content_length = sum(column_content_lengths)
    if total_content_length == 0:
        # Równe szerokości, jeśli nie ma zawartości
        return [usable_width // max_columns] * max_columns

    # Proporcjonalne szerokości na podstawie zawartości
    column_widths = []
    for length in column_content_lengths:
        # Każda kolumna otrzymuje co najmniej 10% szerokości
        min_width = usable_width * 0.1 / max_columns
        # Reszta jest rozdzielana proporcjonalnie
        proportional_width = (length / total_content_length) * usable_width * 0.9
        column_width = int(min_width + proportional_width)

        # Przybliżona szerokość znaku
        char_width = font_types['table_cell']['width'] * 0.6
        text_width = length * char_width

        # Jeśli tekst jest zbyt szeroki, daj tej kolumnie więcej miejsca
        if text_width > column_width:
            column_width = min(int(text_width), int(usable_width * 0.4))

        column_widths.append(column_width)

    # Upewnij się, że suma szerokości nie przekracza dostępnej szerokości
    while sum(column_widths) > usable_width:
        max_index = column_widths.index(max(column_widths))
        column_widths[max_index] -= 1

    return column_widths