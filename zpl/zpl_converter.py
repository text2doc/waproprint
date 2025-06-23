#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_converter.py

"""
Główna klasa konwertera HTML do formatu ZPL (Zebra Programming Language)
"""

import logging
from bs4 import BeautifulSoup, NavigableString, Tag

# Importy funkcji z oddzielnych plików
from zpl.zpl_parse_html import parse_html
from zpl.zpl_calculate_dimensions import calculate_element_dimensions
from zpl.zpl_render_text import render_text_block
# from zpl.zpl_render_table import render_table
from zpl.zpl_encoding import get_encoding_command
from zpl.zpl_text_utils import clean_text


# Modyfikacja w pliku zpl_render_table.py
def render_table(table, start_x, start_y, max_width, font_types, render_text_block_func):
    """
    Generuje kod ZPL dla tabeli HTML z proporcjonalnymi szerokościami kolumn

    Args:
        table (BeautifulSoup): Element tabeli
        start_x (int): Początkowa pozycja X
        start_y (int): Początkowa pozycja Y
        max_width (int): Maksymalna szerokość tabeli
        font_types (dict): Definicje czcionek
        render_text_block_func (function): Funkcja do renderowania tekstu

    Returns:
        tuple: Wygenerowany kod ZPL i nowa pozycja Y
    """
    zpl = []
    current_y = start_y

    # Znajdź wszystkie wiersze tabeli
    rows = table.find_all('tr', recursive=False)
    if not rows:
        # Spróbuj znaleźć wiersze w tbody, thead lub tfoot
        for section in table.find_all(['tbody', 'thead', 'tfoot'], recursive=False):
            rows.extend(section.find_all('tr', recursive=False))

    # Ustal liczbę kolumn na podstawie wiersza z największą liczbą komórek
    max_columns = max([len(row.find_all(['td', 'th'], recursive=False))
                      for row in rows]) if rows else 0

    # Definiowanie szerokości kolumn (proporcja całkowitej szerokości)
    # Pierwsza kolumna (Lp.) będzie miała tylko 8% szerokości tabeli
    column_widths_percent = [8]  # Lp. - wąska kolumna (8%)

    # Pozostałe szerokości kolumn w zależności od liczby kolumn
    if max_columns == 5:  # Dla tabeli z 5 kolumnami
        # [Lp.][Nazwa towaru][Ilość/J. miary][Cena netto][Rabat]
        column_widths_percent.extend([38, 18, 18, 18])  # Suma = 100%
    elif max_columns == 6:  # Dla tabeli z 6 kolumnami
        # [Lp.][Nazwa towaru][Ilość/J. miary][Cena netto][Rabat][Wartość]
        column_widths_percent.extend([32, 15, 15, 15, 15])  # Suma = 100%
    else:
        # Domyślnie: równy podział pozostałej przestrzeni
        remaining_percent = 92  # 100% - 8% (dla pierwszej kolumny)
        remaining_columns = max_columns - 1
        if remaining_columns > 0:
            percent_per_column = remaining_percent / remaining_columns
            column_widths_percent.extend(
                [percent_per_column] * remaining_columns)

    # Przelicz procenty na rzeczywiste szerokości w punktach
    available_width = max_width - 2 * start_x
    column_widths = [int(available_width * percent / 100)
                     for percent in column_widths_percent]

    # Jeśli mamy mniej zdefiniowanych szerokości niż kolumn, dodaj brakujące
    while len(column_widths) < max_columns:
        column_widths.append(int(available_width / max_columns))

    # Przetwórz każdy wiersz
    for row_index, row in enumerate(rows):
        cells = row.find_all(['td', 'th'], recursive=False)

        max_cell_height = 0  # Wysokość najwyższej komórki w wierszu

        # Dodaj linię oddzielającą wiersze
        zpl.append(
            f"^FO{start_x},{current_y}^GB{max_width - 2 * start_x},1,1^FS")
        current_y += 10  # Odstęp po linii

        # Oblicz pozycje początkowe dla każdej kolumny
        column_positions = [start_x]
        for i in range(1, max_columns):
            column_positions.append(
                column_positions[i - 1] + column_widths[i - 1])

        # Przetwórz każdą komórkę w wierszu
        for col_index, cell in enumerate(cells):
            if col_index >= max_columns:
                break  # Zabezpieczenie przed przekroczeniem liczby kolumn

            # Uwzględnij atrybut colspan jeśli istnieje
            colspan = int(cell.get('colspan', 1))
            cell_x = column_positions[col_index]

            # Oblicz szerokość komórki z uwzględnieniem colspan
            if colspan > 1 and col_index + colspan <= len(column_widths):
                cell_width = sum(column_widths[col_index:col_index + colspan])
            else:
                cell_width = column_widths[col_index]

            # Pobierz tekst komórki, usuwając niepotrzebne spacje
            cell_text = cell.get_text().strip()

            # Określ typ czcionki na podstawie typu komórki
            font_type = 'small' if cell.name == 'th' else 'table_cell'

            # Dla multi-wierszowego tekstu w komórce, podziel na linie
            lines = cell_text.split('\n')

            # Zainicjuj wysokość komórki
            cell_height = 0

            # Renderuj każdą linię w komórce
            line_y = current_y
            for line in lines:
                line = line.strip()
                if line:
                    # Renderuj tekst z pełną szerokością komórki
                    line_zpl, new_line_y = render_text_block_func(
                        line,
                        cell_x + 5,  # Dodaj małe wcięcie
                        line_y,
                        font_type=font_type,
                        width=cell_width - 10,  # Zostaw margines z obu stron
                        alignment='L'  # Domyślne wyrównanie do lewej
                    )
                    zpl.append(line_zpl)

                    # Oblicz wysokość tekstu na podstawie użytej czcionki
                    font_height = font_types[font_type]['height']

                    # Aktualizuj pozycję Y dla następnej linii w tej komórce
                    line_y = new_line_y + font_height // 2

                    # Aktualizuj wysokość komórki
                    cell_height = line_y - current_y

            # Aktualizuj maksymalną wysokość wiersza
            if cell_height > max_cell_height:
                max_cell_height = cell_height

        # Aktualizuj pozycję Y na podstawie najwyższej komórki w wierszu
        current_y += max_cell_height + 15  # Odstęp po wierszu

    # Dodaj ostatnią linię na dole tabeli
    zpl.append(f"^FO{start_x},{current_y}^GB{max_width - 2 * start_x},1,1^FS")
    current_y += 15  # Odstęp po tabeli

    return "\n".join(zpl), current_y


class HtmlToZpl:
    def __init__(self,
                 printer_name=None,
                 dpi=203,
                 label_width=4.0,
                 label_height=6.0,
                 font_size=0,
                 encoding='cp852',
                 interactive=False):
        """
        Inicjalizuje konwerter HTML do ZPL

        Args:
            printer_name (str): Nazwa drukarki Zebra
            dpi (int): Rozdzielczość drukarki w DPI (typowo 203 lub 300)
            label_width (float): Szerokość etykiety w calach
            label_height (float): Wysokość etykiety w calach (0 dla automatycznego określenia)
            font_size (int): Podstawowy rozmiar czcionki (0-9 dla wbudowanych czcionek Zebra)
            encoding (str): Kodowanie znaków
            interactive (bool): Tryb interaktywny
        """
        self.printer_name = printer_name
        self.dpi = dpi
        self.label_width = label_width
        self.label_height = label_height
        self.font_size = font_size
        self.encoding = encoding
        self.interactive = interactive

        # Przeliczenie wymiarów na punkty (dots)
        self.width_dots = int(self.label_width * self.dpi)

        # Jeśli wysokość jest 0, będziemy ją obliczać dynamicznie
        if self.label_height > 0:
            self.height_dots = int(self.label_height * self.dpi)
        else:
            self.height_dots = 0  # Będzie obliczone podczas przetwarzania

        # Margines (w punktach)
        self.margin_dots = int(0.1 * self.dpi)  # 0.1 cala marginesu

        # Odstęp między liniami (w punktach)
        self.line_spacing = int(0.15 * self.dpi)  # 0.15 cala między liniami

        # Domyślne czcionki i rozmiary
        self.font_types = {
            'header': {'name': '0', 'width': 40, 'height': 40},
            'subheader': {'name': '0', 'width': 30, 'height': 30},
            'normal': {'name': '0', 'width': 25, 'height': 25},
            'small': {'name': '0', 'width': 20, 'height': 20},
            'table_header': {'name': '0', 'width': 25, 'height': 25},
            'table_cell': {'name': '0', 'width': 20, 'height': 20}
        }

        logging.info(f"Inicjalizacja konwertera HTML do ZPL")
        logging.info(f"Drukarka: {self.printer_name}")
        logging.info(f"Rozdzielczość: {self.dpi} DPI")
        logging.info(
            f"Wymiary etykiety: {self.label_width}\" x {self.label_height}\" ({self.width_dots} x {self.height_dots} punktów)")
        logging.info(f"Kodowanie: {self.encoding}")

    def _get_encoding_command(self):
        """Zwraca komendę ZPL dla wybranego kodowania"""
        return get_encoding_command(self.encoding)

    def _clean_text(self, text):
        """Czyści tekst do wydruku w ZPL, usuwając problematyczne znaki"""
        return clean_text(text)

    def _calculate_element_dimensions(self, soup):
        """
        Oblicza przybliżone wymiary dokumentu HTML w jednostkach ZPL

        Args:
            soup (BeautifulSoup): Sparsowany dokument HTML

        Returns:
            int: Szacowana wysokość dokumentu w punktach
        """
        return calculate_element_dimensions(soup, self.dpi, self.margin_dots, self.font_types)

    def _parse_html(self, html_content):
        """Parsuje HTML i przygotowuje do konwersji"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Jeśli nie określono wysokości etykiety, oblicz ją na podstawie zawartości
            if self.height_dots == 0:
                estimated_height = self._calculate_element_dimensions(soup)
                self.height_dots = estimated_height
                logging.info(
                    f"Automatycznie ustalona wysokość etykiety: {self.height_dots} punktów ({self.height_dots / self.dpi:.2f}\")")

            return soup
        except Exception as e:
            logging.error(f"Błąd podczas parsowania HTML: {e}")
            raise

    def _render_text_block(self, text, x, y, font_type='normal', width=0, alignment='L'):
        """
        Generuje kod ZPL dla bloku tekstu

        Args:
            text (str): Tekst do wyświetlenia
            x (int): Pozycja X
            y (int): Pozycja Y
            font_type (str): Typ czcionki (header, subheader, normal, small)
            width (int): Szerokość pola tekstowego (0 = automatyczna)
            alignment (str): Wyrównanie tekstu (L, C, R)

        Returns:
            tuple: Wygenerowany kod ZPL i nowa pozycja Y
        """
        return render_text_block(text, x, y, self.font_types, font_type, width, alignment, self._clean_text)

    def _render_table(self, table, start_x, start_y):
        """
        Generuje kod ZPL dla tabeli HTML

        Args:
            table (BeautifulSoup): Element tabeli
            start_x (int): Początkowa pozycja X
            start_y (int): Początkowa pozycja Y

        Returns:
            tuple: Wygenerowany kod ZPL i nowa pozycja Y
        """
        return render_table(table, start_x, start_y, self.width_dots, self.font_types, self._render_text_block)

    def _render_barcode(self, barcode_data, x, y):
        """
        Generuje kod ZPL dla kodu kreskowego

        Args:
            barcode_data (str): Dane do zakodowania
            x (int): Pozycja X
            y (int): Pozycja Y

        Returns:
            tuple: Wygenerowany kod ZPL i nowa pozycja Y
        """
        # Kod kreskowy CODE128
        zpl = []
        zpl.append(f"^FO{x},{y}")  # Pozycja początkowa
        # Kod kreskowy CODE128, wysokość 100, czytelny, bez rotacji
        zpl.append("^BCN,100,Y,N,N")
        zpl.append(f"^FD{barcode_data}")  # Dane do zakodowania
        zpl.append("^FS")  # Koniec pola
        # 150 punktów na kod kreskowy + margines
        return "\n".join(zpl), y + 150

    def html_to_zpl(self, html_content):
        """
        Konwertuje HTML do kodu ZPL

        Args:
            html_content (str): Zawartość HTML do konwersji

        Returns:
            str: Wygenerowany kod ZPL
        """
        # Parsuj HTML
        soup = self._parse_html(html_content)

        # Rozpocznij generowanie kodu ZPL
        zpl = []

        # Rozpoczęcie formatu ZPL
        zpl.append("^XA")

        # Resetowanie drukarki i ustawienie domyślnych parametrów
        zpl.append("^JA")

        # Ustaw szerokość etykiety
        zpl.append(f"^PW{self.width_dots}")

        # Ustawienie wysokości etykiety
        zpl.append(f"^LL{self.height_dots}")

        # Ustaw początek układu współrzędnych
        zpl.append("^LH0,0")

        # Ustaw kodowanie
        zpl.append(self._get_encoding_command())

        # Ustaw typ nośnika
        zpl.append("^MTD")  # Typ materiału: termiczny direct

        # Pozycja Y do śledzenia aktualnej pozycji na etykiecie
        current_y = self.margin_dots

        # Sprawdź, czy istnieje kod kreskowy w HTML
        barcode_svg = soup.find('svg', {'id': 'barcode'})
        if barcode_svg:
            # Pobierz dane kodu kreskowego z atrybutu data-barcode
            barcode_data = barcode_svg.get('data-barcode', '')
            if barcode_data:
                # Dodaj kod kreskowy w prawym górnym rogu
                barcode_zpl, current_y = self._render_barcode(
                    barcode_data, self.width_dots - 250, self.margin_dots)
                zpl.append(barcode_zpl)

        # Funkcja rekurencyjna do przetwarzania elementów HTML
        def process_element(element, level=0):
            nonlocal current_y

            # Pomiń elementy style, script, meta, itp.
            if element.name in ['style', 'script', 'meta', 'link', 'head']:
                return

            # Dla elementów HTML
            if isinstance(element, Tag):
                # Przetwórz tabele
                if element.name == 'table':
                    table_zpl, current_y = self._render_table(
                        element,
                        self.margin_dots,
                        current_y
                    )
                    zpl.append(table_zpl)
                    return

                # Dla elementów blokowych
                if element.name in ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Wybierz rodzaj czcionki
                    font_type = 'normal'
                    if element.name == 'h1':
                        font_type = 'header'
                    elif element.name == 'h2':
                        font_type = 'subheader'
                    elif element.name in ['h3', 'h4']:
                        font_type = 'normal'

                    # Pobierz bezpośredni tekst elementu (bez tekstu dzieci)
                    text = ''.join(child.string for child in element.children
                                   if isinstance(child, NavigableString) and child.string.strip())

                    if text.strip():
                        # Renderuj tekst elementu
                        zpl_text, current_y = self._render_text_block(
                            text.strip(),
                            self.margin_dots,
                            current_y,
                            font_type=font_type,
                            width=self.width_dots - 2 * self.margin_dots
                        )
                        zpl.append(zpl_text)
                        current_y += 5  # Dodaj mały odstęp

                    # Przetwórz pozostałe elementy
                    for child in element.children:
                        if isinstance(child, Tag):
                            process_element(child, level + 1)
                    return

                # Przetwórz pozostałe elementy
                for child in element.children:
                    if isinstance(child, (NavigableString, Tag)):
                        process_element(child, level + 1)

            # Dla tekstów
            elif isinstance(element, NavigableString):
                if element.strip():
                    # Renderuj tekst tylko jeśli nie jest w komórce tabeli
                    parent = element.parent
                    if parent and parent.name not in ['td', 'th']:
                        # Renderuj tekst z domyślnym rozmiarem czcionki
                        zpl_text, current_y = self._render_text_block(
                            element.strip(),
                            self.margin_dots,
                            current_y,
                            font_type='normal',
                            width=self.width_dots - 2 * self.margin_dots
                        )
                        zpl.append(zpl_text)

        # Znajdź element body
        body = soup.find('body')
        if body:
            # Przetwórz zawartość body
            for child in body.children:
                if not isinstance(child, NavigableString) or child.strip():
                    process_element(child)
        else:
            # Jeśli nie ma body, przetwórz cały dokument
            for child in soup.children:
                if not isinstance(child, NavigableString) or child.strip():
                    process_element(child)

        # Zakończenie formatu ZPL
        zpl.append("^PQ1")  # Drukuj 1 etykietę
        zpl.append("^XZ")

        return "\n".join(zpl)
