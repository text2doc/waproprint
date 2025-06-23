import logging
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import html
import cssutils
import tinycss
from collections import defaultdict


class HtmlToZplConverter:
    """
    Konwerter HTML z tabelami do formatu ZPL z zachowaniem układu i stylowania CSS
    """

    def __init__(self,
                 printer_name=None,
                 dpi=203,
                 label_width=4.0,
                 label_height=6.0,
                 font_size=0,
                 encoding='cp852',
                 interactive=False):
        """
        Inicjalizacja konwertera HTML do ZPL

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

        # Domyślne czcionki i rozmiary
        self.font_types = {
            'header': {'name': '0', 'width': 40, 'height': 40},
            'subheader': {'name': '0', 'width': 30, 'height': 30},
            'normal': {'name': '0', 'width': 25, 'height': 25},
            'small': {'name': '0', 'width': 20, 'height': 20},
            # Nagłówek tabeli używa small
            'table_header': {'name': '0', 'width': 20, 'height': 20},
            'table_cell': {'name': '0', 'width': 25, 'height': 25}
        }

        # Rejestr zajętych pozycji Y (dla zapobiegania nakładaniu linii)
        self.y_positions_registry = []

        # Minimalny odstęp między liniami (w punktach)
        self.min_line_spacing = 10

        # Mapowanie atrybutów CSS na parametry ZPL
        self.css_mappings = {
            'text-align': {
                'left': 'L',
                'center': 'C',
                'right': 'R',
                'justify': 'J'
            },
            'font-weight': {
                'bold': True,
                'normal': False
            }
        }

        # Mapa szerokości kolumn dla tabeli
        self.table_column_widths = {}

        logging.info(f"Inicjalizacja konwertera HTML do ZPL")
        logging.info(f"Drukarka: {self.printer_name}")
        logging.info(f"Rozdzielczość: {self.dpi} DPI")
        logging.info(
            f"Wymiary etykiety: {self.label_width}\" x {self.label_height}\" ({self.width_dots} x {self.height_dots} punktów)")
        logging.info(f"Kodowanie: {self.encoding}")

    def _get_encoding_command(self):
        """Zwraca komendę ZPL dla wybranego kodowania"""
        encodings = {
            'cp850': '^CI28',  # Codepage 850
            'cp852': '^CI29',  # Codepage 852
            'cp437': '^CI0',  # US Standard Code Page
            'utf8': '^CI28',  # UTF-8 (najlepsze przybliżenie)
            'iso8859-1': '^CI27',  # ISO 8859-1 Latin 1
            # ISO 8859-2 Latin 2 (najlepsze przybliżenie)
            'iso8859-2': '^CI29',
            'windows-1250': '^CI29',  # Windows-1250 (najlepsze przybliżenie)
            'windows-1252': '^CI27'  # Windows-1252 (najlepsze przybliżenie)
        }
        return encodings.get(self.encoding.lower(), '^CI28')

    def _clean_text(self, text):
        """
        Czyści tekst do wydruku w ZPL, usuwając problematyczne znaki

        Args:
            text (str): Tekst do oczyszczenia

        Returns:
            str: Oczyszczony tekst
        """
        if text is None:
            return ""

        # Usunięcie znaków sterujących
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)

        # Przetworzenie znaków specjalnych ZPL (^)
        text = text.replace('^', '\\^')

        # Przetworzenie znaków specjalnych ZPL (~)
        text = text.replace('~', '\\~')

        # Konwersja znaku nowej linii na spację
        text = text.replace('\n', ' ').replace('\r', '')

        # Usunięcie podwójnych spacji
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _parse_html(self, html_content):
        """
        Parsuje HTML i przygotowuje do konwersji

        Args:
            html_content (str): Zawartość HTML do konwersji

        Returns:
            BeautifulSoup: Sparsowany dokument HTML
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Jeśli nie określono wysokości etykiety, oblicz ją na podstawie zawartości
            if self.height_dots == 0:
                # Dodaj logikę do estymacji wysokości na podstawie zawartości
                self.height_dots = 6000  # Przykładowa wartość
                logging.info(
                    f"Automatycznie ustalona wysokość etykiety: {self.height_dots} punktów ({self.height_dots / self.dpi:.2f}\")")

            # Ekstrakcja i parsowanie stylów CSS
            self._extract_and_parse_css(soup)

            return soup
        except Exception as e:
            logging.error(f"Błąd podczas parsowania HTML: {e}")
            raise

    def _extract_and_parse_css(self, soup):
        """
        Ekstrahuje i parsuje style CSS z dokumentu HTML

        Args:
            soup (BeautifulSoup): Sparsowany dokument HTML
        """
        self.css_rules = {}

        # Pobierz wszystkie tagi style
        style_tags = soup.find_all('style')
        for style_tag in style_tags:
            style_content = style_tag.string
            if style_content:
                # Parsowanie CSS
                try:
                    # Wyłącz zbędne logi
                    cssutils.log.setLevel(logging.CRITICAL)
                    sheet = cssutils.parseString(style_content)
                    for rule in sheet:
                        if rule.type == rule.STYLE_RULE:
                            selector = rule.selectorText
                            properties = {}
                            for property in rule.style:
                                properties[property.name] = property.value
                            self.css_rules[selector] = properties
                except Exception as e:
                    logging.warning(f"Błąd podczas parsowania CSS: {e}")

    def _get_css_properties(self, element):
        """
        Pobiera właściwości CSS dla elementu na podstawie jego klasy i ID

        Args:
            element (Tag): Element HTML

        Returns:
            dict: Słownik właściwości CSS
        """
        properties = {}

        # Sprawdź wszystkie pasujące selektory
        for selector, props in self.css_rules.items():
            # Sprawdź selektory tagów
            if selector == element.name:
                properties.update(props)

            # Sprawdź selektory klas
            if 'class' in element.attrs:
                for cls in element['class']:
                    if selector == f'.{cls}':
                        properties.update(props)

            # Sprawdź selektor ID
            if 'id' in element.attrs and selector == f'#{element["id"]}':
                properties.update(props)

        # Sprawdź style inline
        if 'style' in element.attrs:
            style_text = element['style']
            try:
                inline_style = cssutils.parseStyle(style_text)
                for property in inline_style:
                    properties[property.name] = property.value
            except Exception as e:
                logging.warning(f"Błąd podczas parsowania stylu inline: {e}")

        return properties

    def _get_safe_y_position(self, y_pos, height=20):
        """
        Zapewnia, że linia nie nakłada się na poprzednią

        Args:
            y_pos (int): Proponowana pozycja Y
            height (int): Wysokość tekstu/elementu

        Returns:
            int: Bezpieczna pozycja Y
        """
        # Sprawdź, czy pozycja Y jest już zajęta (z marginesem tolerancji)
        for used_y in self.y_positions_registry:
            if abs(used_y - y_pos) < height:
                # Pozycja zajęta, przesuń w dół o wysokość + odstęp
                return self._get_safe_y_position(y_pos + height + self.min_line_spacing, height)

        # Pozycja jest bezpieczna, zapisz ją i zwróć
        self.y_positions_registry.append(y_pos)
        return y_pos

    def _render_text_block(self, text, x, y, font_type='normal', width=0, alignment='L', is_bold=False):
        """
        Generuje kod ZPL dla bloku tekstu

        Args:
            text (str): Tekst do wyświetlenia
            x (int): Pozycja X
            y (int): Pozycja Y
            font_type (str): Typ czcionki (header, subheader, normal, small)
            width (int): Szerokość pola tekstowego (0 = automatyczna)
            alignment (str): Wyrównanie tekstu (L, C, R, J)
            is_bold (bool): Czy tekst ma być pogrubiony

        Returns:
            tuple: Wygenerowany kod ZPL i nowa pozycja Y
        """
        # Zabezpieczenie przed pustym tekstem
        if not text or not text.strip():
            return "", y

        # Pobierz parametry czcionki
        font = self.font_types.get(font_type, self.font_types['normal'])
        font_name = font['name']
        font_width = font['width']
        font_height = font['height']

        # Określenie szerokości pola tekstowego
        field_width = width if width > 0 else self.width_dots - x - self.margin_dots

        # Znajdź bezpieczną pozycję Y
        safe_y = self._get_safe_y_position(y, font_height)

        # Oblicz szacowaną wysokość tekstu
        text_length = len(text)
        chars_per_line = field_width // font_width if font_width > 0 else 40
        lines_count = (text_length // chars_per_line) + 1
        estimated_height = lines_count * font_height

        # Generuj kod ZPL
        zpl = []

        # Field Origin - pozycja początkowa
        zpl.append(f"^FO{x},{safe_y}")

        # Wybierz czcionkę
        zpl.append(f"^A{font_name}N,{font_height},{font_width}")

        # Field Block - parametry bloku tekstu
        zpl.append(f"^FB{field_width},1,0,{alignment}")

        # Field Data - dane tekstowe
        zpl.append(f"^FD{self._clean_text(text)}")

        # Field Separator - koniec pola
        zpl.append("^FS")

        # Oblicz nową pozycję Y
        new_y = safe_y + estimated_height

        return "\n".join(zpl), new_y

    def _render_table(self, table, start_x, start_y):
        """
        Generuje kod ZPL dla tabeli HTML z proporcjonalnymi szerokościami kolumn
        i zabezpieczeniem przed nachodzeniem linii tekstu na siebie

        Args:
            table (BeautifulSoup): Element tabeli
            start_x (int): Początkowa pozycja X
            start_y (int): Początkowa pozycja Y

        Returns:
            tuple: Wygenerowany kod ZPL i nowa pozycja Y
        """
        zpl = []
        current_y = start_y
        max_width = self.width_dots

        # Resetuj rejestr pozycji Y dla nowej tabeli
        self.y_positions_registry = []

        # Analizuj strukturę tabeli i zbierz dane o kolumnach
        table_data = self._analyze_table_structure(table)
        rows = table_data['rows']
        column_count = table_data['column_count']

        # Obliczanie szerokości kolumn na podstawie CSS lub auto-detekcji
        column_widths = self._calculate_column_widths(
            table, column_count, max_width - 2 * start_x)

        # Oblicz pozycje początkowe dla każdej kolumny
        column_positions = [start_x]
        for i in range(1, column_count):
            column_positions.append(
                column_positions[i - 1] + column_widths[i - 1])

        # Dodaj poziomą linię na początku tabeli
        horizontal_line_y = self._get_safe_y_position(current_y)
        zpl.append(
            f"^FO{start_x},{horizontal_line_y}^GB{max_width - 2 * start_x},1,1^FS")
        current_y = horizontal_line_y + 15  # Odstęp po linii poziomej

        # Przetwórz każdy wiersz
        for row_index, row in enumerate(rows):
            cells = row
            max_cell_height = 0

            # Przetwórz każdą komórkę w wierszu
            for col_index, cell in enumerate(cells):
                if 'skip' in cell and cell['skip']:
                    # Pomijamy już przetworzone komórki (część colspan/rowspan)
                    continue

                # Pobierz dane komórki
                cell_tag = cell['tag']
                cell_text = cell['text']
                colspan = cell['colspan']
                rowspan = cell['rowspan']
                cell_type = 'table_header' if cell_tag.name == 'th' else 'table_cell'

                # Pobierz właściwości CSS
                css_props = self._get_css_properties(cell_tag)

                # Określ wyrównanie tekstu
                text_align = self.css_mappings['text-align'].get(
                    css_props.get('text-align', 'left'), 'L')

                # Określ, czy tekst ma być pogrubiony
                is_bold = self.css_mappings['font-weight'].get(
                    css_props.get('font-weight', 'normal'), False)

                # Oblicz pozycję X i szerokość komórki z uwzględnieniem colspan
                cell_x = column_positions[col_index]
                if colspan > 1 and col_index + colspan <= len(column_widths):
                    cell_width = sum(
                        column_widths[col_index:col_index + colspan])
                else:
                    cell_width = column_widths[col_index]

                # Dla multi-wierszowego tekstu w komórce, podziel na linie
                lines = cell_text.split('\n')

                # Renderuj każdą linię w komórce
                line_y = current_y
                cell_height = 0

                for line in lines:
                    line = line.strip()
                    if line:
                        # Renderuj tekst z pełną szerokością komórki
                        line_zpl, new_line_y = self._render_text_block(
                            line,
                            cell_x + 5,  # Dodaj małe wcięcie
                            line_y,
                            font_type=cell_type,
                            width=cell_width - 10,  # Zostaw margines z obu stron
                            alignment=text_align,
                            is_bold=is_bold
                        )
                        zpl.append(line_zpl)

                        # Aktualizuj pozycję Y dla następnej linii w tej komórce
                        font_height = self.font_types[cell_type]['height']
                        line_y = new_line_y + font_height // 2

                        # Aktualizuj wysokość komórki
                        cell_height = line_y - current_y

                # Aktualizuj maksymalną wysokość wiersza
                if cell_height > max_cell_height:
                    max_cell_height = cell_height

                # Oznacz komórki w przypadku rowspan dla następnych wierszy
                if rowspan > 1 and row_index + rowspan <= len(rows):
                    for r in range(1, rowspan):
                        for c in range(colspan):
                            if col_index + c < len(rows[row_index + r]):
                                rows[row_index + r][col_index + c]['skip'] = True

            # Aktualizuj pozycję Y na podstawie najwyższej komórki w wierszu
            # Zapewnij minimalny odstęp między wierszami
            font_height = max(self.font_types['table_cell']['height'],
                              self.font_types['table_header']['height'])
            current_y += max(max_cell_height, font_height * 2) + 20

            # Dodaj poziomą linię na końcu wiersza
            horizontal_line_y = self._get_safe_y_position(current_y - 10)
            zpl.append(
                f"^FO{start_x},{horizontal_line_y}^GB{max_width - 2 * start_x},1,1^FS")
            current_y = horizontal_line_y + 15  # Odstęp po linii poziomej

        return "\n".join(zpl), current_y

    def _analyze_table_structure(self, table):
        """
        Analizuje strukturę tabeli HTML

        Args:
            table (BeautifulSoup): Element tabeli

        Returns:
            dict: Informacje o strukturze tabeli
        """
        # Znajdź wszystkie wiersze tabeli
        html_rows = table.find_all('tr', recursive=True)

        # Inicjalizuj strukturę danych dla tabeli
        rows = []
        column_count = 0

        # Przetwórz każdy wiersz
        for row in html_rows:
            cells = []
            # Znajdź wszystkie komórki w wierszu
            for cell in row.find_all(['td', 'th'], recursive=False):
                cell_data = {
                    'tag': cell,
                    'text': cell.get_text().strip(),
                    'colspan': int(cell.get('colspan', 1)),
                    'rowspan': int(cell.get('rowspan', 1)),
                    'skip': False
                }
                cells.append(cell_data)

            rows.append(cells)

            # Aktualizuj liczbę kolumn
            row_cells_count = sum(cell['colspan'] for cell in cells)
            if row_cells_count > column_count:
                column_count = row_cells_count

        return {
            'rows': rows,
            'column_count': column_count
        }

    def _calculate_column_widths(self, table, column_count, available_width):
        """
        Oblicza szerokości kolumn na podstawie CSS lub auto-detekcji

        Args:
            table (BeautifulSoup): Element tabeli
            column_count (int): Liczba kolumn
            available_width (int): Dostępna szerokość

        Returns:
            list: Lista szerokości kolumn
        """
        # Sprawdź, czy mamy szerokości kolumn w CSS
        css_widths = []

        # Sprawdź tag colgroup i col
        colgroup = table.find('colgroup')
        if colgroup:
            for col_index, col in enumerate(colgroup.find_all('col')):
                width_str = col.get('width', '')
                if width_str.endswith('%'):
                    try:
                        width_percent = float(width_str.rstrip('%'))
                        width_px = (width_percent / 100) * available_width
                        css_widths.append(int(width_px))
                    except ValueError:
                        pass

        # Jeśli mamy kompletne szerokości z CSS, użyj ich
        if len(css_widths) == column_count:
            return css_widths

        # Jeśli nie mamy szerokości z CSS, oblicz proporcjonalnie
        # Pierwsza kolumna (Lp.) będzie miała tylko 8% szerokości tabeli
        column_widths_percent = [8]  # Lp. - wąska kolumna (8%)

        # Pozostałe szerokości kolumn w zależności od liczby kolumn
        if column_count == 5:  # Dla tabeli z 5 kolumnami
            # [Lp.][Nazwa towaru][Ilość/J. miary][Cena netto][Rabat]
            column_widths_percent.extend([38, 18, 18, 18])  # Suma = 100%
        elif column_count == 6:  # Dla tabeli z 6 kolumnami
            # [Lp.][Nazwa towaru][Ilość/J. miary][Cena netto][Rabat][Wartość]
            column_widths_percent.extend([32, 15, 15, 15, 15])  # Suma = 100%
        elif column_count == 7:  # Dla tabeli z 7 kolumnami
            # [Lp.][Nazwa towaru][Ilość/J. miary][Cena netto][Rabat][Cena jedn.][Wartość]
            column_widths_percent.extend(
                [30, 12, 13, 12, 13, 12])  # Suma = 100%
        else:
            # Domyślnie: równy podział pozostałej przestrzeni
            remaining_percent = 92  # 100% - 8% (dla pierwszej kolumny)
            remaining_columns = column_count - 1
            if remaining_columns > 0:
                percent_per_column = remaining_percent / remaining_columns
                column_widths_percent.extend(
                    [percent_per_column] * remaining_columns)

        # Przelicz procenty na rzeczywiste szerokości w punktach
        column_widths = [int(available_width * percent / 100)
                         for percent in column_widths_percent]

        # Jeśli mamy mniej zdefiniowanych szerokości niż kolumn, dodaj brakujące
        while len(column_widths) < column_count:
            column_widths.append(int(available_width / column_count))

        # Przytnij listę do wymaganej liczby kolumn
        return column_widths[:column_count]

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
        if not barcode_data or barcode_data.lower() == 'none':
            return "", y

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
                barcode_zpl, _ = self._render_barcode(
                    barcode_data, self.width_dots - 250, self.margin_dots)
                zpl.append(barcode_zpl)

        # Rejestr zajętych pozycji Y
        self.y_positions_registry = []

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
                    table_zpl, new_y = self._render_table(
                        element,
                        self.margin_dots,
                        current_y
                    )
                    zpl.append(table_zpl)
                    current_y = new_y + 20  # Dodaj odstęp po tabeli
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

                    # Pobierz właściwości CSS
                    css_props = self._get_css_properties(element)

                    # Określ wyrównanie tekstu
                    text_align = self.css_mappings['text-align'].get(
                        css_props.get('text-align', 'left'), 'L')

                    # Określ, czy tekst ma być pogrubiony
                    is_bold = self.css_mappings['font-weight'].get(
                        css_props.get('font-weight', 'normal'), False)

                    # Pobierz bezpośredni tekst elementu (bez tekstu dzieci)
                    direct_text = ''.join(child.string for child in element.children
                                          if isinstance(child, NavigableString) and child.string.strip())

                    if direct_text.strip():
                        # Renderuj tekst elementu
                        text_zpl, new_y = self._render_text_block(
                            direct_text.strip(),
                            self.margin_dots,
                            current_y,
                            font_type=font_type,
                            width=self.width_dots - 2 * self.margin_dots,
                            alignment=text_align,
                            is_bold=is_bold
                        )
                        zpl.append(text_zpl)
                        current_y = new_y + 5  # Dodaj mały odstęp

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
                        safe_y = self._get_safe_y_position(
                            current_y, self.font_types['normal']['height'])
                        text_zpl, new_y = self._render_text_block(
                            element.strip(),
                            self.margin_dots,
                            safe_y,
                            font_type='normal',
                            width=self.width_dots - 2 * self.margin_dots
                        )
                        zpl.append(text_zpl)
                        current_y = new_y + self.min_line_spacing

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


# Przykład użycia:
if __name__ == "__main__":
    # Inicjalizacja konwertera
    converter = HtmlToZplConverter(
        printer_name="Zebra_ZT410",
        dpi=203,
        label_width=6.0,
        label_height=0,  # Automatyczna wysokość
        encoding='cp852'
    )

    # Wczytaj plik HTML
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Konwersja do ZPL
        zpl_code = converter.html_to_zpl(html_content)

        # Zapisz wynik do pliku
        output_file = input_file.rsplit('.', 1)[0] + '.zpl'
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(zpl_code)

        print(f"Konwersja zakończona pomyślnie. Zapisano do {output_file}")
    else:
        print("Podaj ścieżkę do pliku HTML jako argument programu")
