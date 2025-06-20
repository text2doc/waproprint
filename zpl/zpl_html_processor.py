#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_html_processor.py

"""
Funkcje do przetwarzania HTML na potrzeby konwersji do formatu ZPL
"""

from bs4 import BeautifulSoup, NavigableString, Tag
import re


def process_html_document(html_content):
    """
    Wstępnie przetwarza dokument HTML przed konwersją do ZPL

    Args:
        html_content (str): Zawartość HTML do przetworzenia

    Returns:
        BeautifulSoup: Przetworzony dokument HTML
    """
    # Parsuj HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Usuń niepotrzebne elementy
    for tag in soup(['script', 'style', 'meta', 'link', 'iframe']):
        tag.decompose()

    # Przetwarzaj tagi BR na znaki nowej linii dla lepszego formatu
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # Przetwarzaj tagi IMG
    for img in soup.find_all('img'):
        # Zastąp obrazki tekstowym opisem
        alt_text = img.get('alt', 'Image')
        img.replace_with(f'[{alt_text}]')

    return soup


def extract_document_structure(soup):
    """
    Ekstrahuje strukturę dokumentu HTML

    Args:
        soup (BeautifulSoup): Sparsowany dokument HTML

    Returns:
        dict: Informacje o strukturze dokumentu
    """
    structure = {
        'title': None,
        'headers': [],
        'sections': [],
        'tables': [],
        'lists': []
    }

    # Pobierz tytuł
    title_tag = soup.find('title')
    if title_tag:
        structure['title'] = title_tag.get_text().strip()

    # Znajdź nagłówki
    for level in range(1, 7):
        headers = soup.find_all(f'h{level}')
        for header in headers:
            structure['headers'].append({
                'level': level,
                'text': header.get_text().strip(),
                'id': header.get('id')
            })

    # Znajdź tabele
    for table in soup.find_all('table'):
        table_info = {
            'rows': len(table.find_all('tr')),
            'columns': 0,
            'has_header': bool(table.find('thead') or table.find('th')),
            'has_footer': bool(table.find('tfoot'))
        }

        # Określ liczbę kolumn na podstawie pierwszego wiersza
        first_row = table.find('tr')
        if first_row:
            table_info['columns'] = len(first_row.find_all(['td', 'th']))

        structure['tables'].append(table_info)

    # Znajdź listy
    for list_tag in soup.find_all(['ul', 'ol']):
        list_info = {
            'type': list_tag.name,
            'items': len(list_tag.find_all('li', recursive=False)),
            'nested': bool(list_tag.find(['ul', 'ol']))
        }
        structure['lists'].append(list_info)

    return structure


def extract_elements_by_type(soup, element_type='table'):
    """
    Ekstrahuje elementy danego typu z dokumentu HTML

    Args:
        soup (BeautifulSoup): Sparsowany dokument HTML
        element_type (str): Typ elementu do wyodrębnienia ('table', 'list', 'header', etc.)

    Returns:
        list: Lista elementów danego typu
    """
    if element_type == 'table':
        return soup.find_all('table')
    elif element_type == 'list':
        return soup.find_all(['ul', 'ol'])
    elif element_type == 'header':
        return soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    elif element_type == 'paragraph':
        return soup.find_all('p')
    elif element_type == 'div':
        return soup.find_all('div')
    else:
        return soup.find_all(element_type)


def normalize_html_for_printing(html_content):
    """
    Normalizuje HTML do wydruku, usuwając zbędne elementy i stylizację

    Args:
        html_content (str): Zawartość HTML do normalizacji

    Returns:
        str: Znormalizowany HTML
    """
    # Parsuj HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Usuń elementy niepotrzebne do druku
    for tag in soup(['script', 'style', 'iframe', 'video', 'audio', 'canvas', 'svg']):
        tag.decompose()

    # Usuń atrybuty stylizacji, zachowując tylko te istotne dla układu
    for tag in soup.find_all(True):
        allowed_attrs = ['id', 'class']
        attrs = dict(tag.attrs)
        for attr in attrs:
            if attr not in allowed_attrs:
                del tag[attr]

    # Usuń puste elementy blokowe
    for tag in soup.find_all(['div', 'p', 'span']):
        if not tag.get_text().strip() and not tag.find_all(True):
            tag.decompose()

    return str(soup)


def extract_content_by_class(soup, class_name):
    """
    Ekstrahuje zawartość elementów o określonej klasie

    Args:
        soup (BeautifulSoup): Sparsowany dokument HTML
        class_name (str): Nazwa klasy do wyszukania

    Returns:
        list: Lista elementów o określonej klasie
    """
    return soup.find_all(class_=class_name)


def extract_data_from_table(table):
    """
    Ekstrahuje dane z tabeli HTML

    Args:
        table (BeautifulSoup): Element tabeli

    Returns:
        list: Dane tabeli w formie listy wierszy, gdzie każdy wiersz jest listą komórek
    """
    data = []

    # Znajdź wszystkie wiersze
    rows = table.find_all('tr')

    for row in rows:
        row_data = []

        # Znajdź komórki (th lub td)
        cells = row.find_all(['th', 'td'])

        for cell in cells:
            # Sprawdź atrybuty colspan i rowspan
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))

            # Pobierz tekst z komórki
            cell_text = cell.get_text().strip()

            # Dodaj tekst do danych wiersza (z informacją o rozpiętości)
            row_data.append({
                'text': cell_text,
                'colspan': colspan,
                'rowspan': rowspan,
                'is_header': cell.name == 'th'
            })

        data.append(row_data)

    return data


def convert_document_fragment(soup, start_tag, end_tag=None):
    """
    Konwertuje fragment dokumentu HTML między określonymi znacznikami

    Args:
        soup (BeautifulSoup): Sparsowany dokument HTML
        start_tag (str): Początkowy znacznik (id, klasa lub selektor)
        end_tag (str): Końcowy znacznik (id, klasa lub selektor), opcjonalny

    Returns:
        BeautifulSoup: Fragment dokumentu
    """
    # Znajdź początkowy element
    start_element = None

    if start_tag.startswith('#'):
        # Szukaj po id
        start_element = soup.find(id=start_tag[1:])
    elif start_tag.startswith('.'):
        # Szukaj po klasie
        start_element = soup.find(class_=start_tag[1:])
    else:
        # Szukaj po nazwie znacznika
        start_element = soup.find(start_tag)

    if not start_element:
        return None

    # Jeśli nie podano końcowego znacznika, zwróć sam początkowy element
    if not end_tag:
        return start_element

    # Znajdź końcowy element
    end_element = None

    if end_tag.startswith('#'):
        # Szukaj po id
        end_element = soup.find(id=end_tag[1:])
    elif end_tag.startswith('.'):
        # Szukaj po klasie
        end_element = soup.find(class_=end_tag[1:])
    else:
        # Szukaj po nazwie znacznika
        end_element = soup.find(end_tag)

    if not end_element:
        return start_element

    # Utwórz nowy dokument zawierający elementy między początkiem a końcem
    fragment = BeautifulSoup('<div></div>', 'html.parser')
    current = start_element

    while current and current != end_element:
        next_sibling = current.next_sibling
        fragment.div.append(current.extract())
        current = next_sibling

    # Dodaj końcowy element
    if current == end_element:
        fragment.div.append(end_element.extract())

    return fragment.div