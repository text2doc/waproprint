#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl_parse_html.py

"""
Funkcje do parsowania HTML dla formatu ZPL
"""

import logging
from bs4 import BeautifulSoup


def parse_html(html_content, calculate_dimensions_func=None, height_dots=0):
    """
    Parsuje HTML i przygotowuje do konwersji

    Args:
        html_content (str): Zawartość HTML do sparsowania
        calculate_dimensions_func (callable): Funkcja do obliczania wymiarów dokumentu
        height_dots (int): Aktualna wysokość etykiety w punktach (0 = automatyczna)

    Returns:
        tuple: (BeautifulSoup, height_dots) - Sparsowany dokument HTML i nowa wysokość
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Jeśli nie określono wysokości etykiety i podano funkcję obliczania wymiarów,
        # oblicz wysokość na podstawie zawartości
        if height_dots == 0 and calculate_dimensions_func:
            estimated_height = calculate_dimensions_func(soup)
            height_dots = estimated_height
            logging.info(
                f"Automatycznie ustalona wysokość etykiety: {height_dots} punktów")

        return soup, height_dots
    except Exception as e:
        logging.error(f"Błąd podczas parsowania HTML: {e}")
        raise


def extract_style_info(element):
    """
    Wyciąga informacje o stylu z elementu HTML

    Args:
        element (Tag): Element HTML

    Returns:
        dict: Słownik z informacjami o stylu
    """
    style_info = {
        'alignment': 'L',  # Domyślnie wyrównanie do lewej
        # Rodzaj czcionki (będzie określony na podstawie tagu)
        'font_type': None,
        'is_bold': False,
        'is_italic': False
    }

    # Sprawdź tag
    if element.name in ['h1', 'h2']:
        style_info['font_type'] = 'header' if element.name == 'h1' else 'subheader'
    elif element.name in ['h3', 'h4']:
        style_info['font_type'] = 'normal'
        style_info['is_bold'] = True
    elif element.name == 'b' or element.name == 'strong':
        style_info['is_bold'] = True
    elif element.name == 'i' or element.name == 'em':
        style_info['is_italic'] = True

    # Sprawdź klasy
    if element.has_attr('class'):
        classes = element['class'] if isinstance(
            element['class'], list) else [element['class']]
        if 'title' in classes:
            style_info['font_type'] = 'header'
            style_info['alignment'] = 'C'
        elif 'subtitle' in classes:
            style_info['font_type'] = 'subheader'
            style_info['alignment'] = 'C'
        elif any(x in classes for x in ['text-center', 'center']):
            style_info['alignment'] = 'C'
        elif any(x in classes for x in ['text-right', 'right']):
            style_info['alignment'] = 'R'
        elif any(x in classes for x in ['currency']):
            style_info['alignment'] = 'R'

    # Sprawdź styl inline
    if element.has_attr('style'):
        style = element['style']
        if 'text-align: center' in style:
            style_info['alignment'] = 'C'
        elif 'text-align: right' in style:
            style_info['alignment'] = 'R'
        if 'font-weight: bold' in style or 'font-weight:bold' in style:
            style_info['is_bold'] = True
        if 'font-style: italic' in style or 'font-style:italic' in style:
            style_info['is_italic'] = True

    return style_info
