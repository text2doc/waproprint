#!/usr/bin/env python
# -*- coding: utf-8 -*-
# html2pdfs/html_processor.py

"""
Moduł do przetwarzania HTML przed konwersją na PDF
"""

import re
import tempfile
import logging

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def preprocess_html(html_file):
    """
    Przetwarza plik HTML, dodając style zapobiegające podziałowi na strony.

    Args:
        html_file (str): Ścieżka do pliku HTML

    Returns:
        str: Ścieżka do przetworzonego pliku HTML
    """
    # Utwórz tymczasowy plik HTML
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as temp_html:
        # Wczytaj oryginalny plik HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # CSS do wymuszenia ciągłego wydruku bez podziału na strony
        continuous_css = """
        <style>
            /* Napraw kolory (czarny tekst, białe tło) */
            html, body {
                background-color: white !important;
                color: black !important;
            }
            * {
                background-color: white !important;
                color: black !important;
            }

            /* Wyłącz całkowicie podziały stron */
            @page {
                size: auto !important;
                margin: 0mm !important;
                padding: 0mm !important;
                height: auto !important;
            }

            @media print {
                @page {
                    size: auto !important;
                    margin: 0mm !important;
                    padding: 0mm !important;
                    height: auto !important;
                }

                body {
                    margin: 0 !important;
                    padding: 0 !important;
                    height: auto !important;
                }
            }

            /* Zapewnij absolutną ciągłość wydruku */
            body, html {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                height: auto !important;
                page-break-after: avoid !important;
                page-break-before: avoid !important;
                page-break-inside: avoid !important;
                overflow: visible !important;
                max-height: none !important;
                min-height: 0 !important;
                position: static !important;
            }

            /* Wyłącz podziały wewnętrzne */
            table, tr, td, th, div, p, h1, h2, h3, h4, h5, h6 {
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                page-break-after: avoid !important;
                page-break-before: avoid !important;
                position: static !important;
            }

            /* Wyłącz wszystkie podziały strony */
            .page-break, div.page, .page, .pagebreak, .page-footer, .page-header, header, footer {
                display: block !important;
                page-break-after: avoid !important;
                page-break-before: avoid !important;
                page-break-inside: avoid !important;
                visibility: visible !important;
                position: static !important;
            }

            /* Fix dla przezroczystości */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }

            /* Absolutne usunięcie wszystkich elementów poza widokiem i pseudo-elementów */
            body::after, body::before, *::after, *::before {
                content: none !important;
                display: none !important;
            }

            /* Usuń wszystkie elementy poza widokiem */
            @media print {
                body::after, body::before, *::after, *::before {
                    display: none !important;
                    content: none !important;
                }

                * {
                    overflow: visible !important;
                }
            }

            /* Wymuszenie ciągłości tabel */
            table {
                page-break-inside: avoid !important;
                page-break-after: avoid !important;
                page-break-before: avoid !important;
                position: static !important;
            }

            /* Usunięcie białych przestrzeni */
            html {
                height: auto !important;
                overflow: visible !important;
                min-height: 0 !important;
            }

            /* Usunięcie marginesów na tabelach */
            table, tr, td, th {
                margin: 0 !important;
                border-spacing: 0 !important;
            }

            /* Absolutne wymuszenie statycznych pozycji */
            * {
                position: static !important;
                float: none !important;
                clear: none !important;
            }

            /* Marker końca dokumentu */
            #document-end-marker {
                display: block !important;
                width: 100% !important;
                height: 1px !important;
                background: transparent !important;
                margin: 0 !important;
                padding: 0 !important;
            }
        </style>
        """

        # Wstaw CSS do tagu head lub na początek pliku jeśli brak tagu head
        if '<head>' in html_content:
            html_content = html_content.replace(
                '<head>', '<head>' + continuous_css)
        else:
            html_content = continuous_css + html_content

        # Upewnij się, że body nie ma zbędnych stylów ani atrybutów wysokości
        html_content = re.sub(
            r'<body[^>]*style="[^"]*height:[^"]*"[^>]*>', '<body>', html_content)
        html_content = re.sub(
            r'<body[^>]*height="[^"]*"[^>]*>', '<body>', html_content)

        # Usuń wszystkie atrybuty stylu które mogą wpływać na wyświetlanie dokumentu
        html_content = re.sub(
            r'style="[^"]*page-break[^"]*"', 'style=""', html_content)

        # Dodaj znacznik końca dokumentu
        html_content = html_content.replace(
            '</body>', '<div id="document-end-marker"></div></body>')

        # Upewnij się, że HTML jest poprawny - dodaj brakujące tagi jeśli to konieczne
        if '<html' not in html_content:
            html_content = '<html><head></head><body>' + html_content + '</body></html>'

        # Zmodyfikuj wszystkie tabele aby miały jednolite marginesy i spacing
        html_content = re.sub(r'<table[^>]*>', '<table style="border-spacing:0; margin:0; border-collapse:collapse;">',
                              html_content)

        # Ustaw sztywne wymiary komórek aby zapobiec niepożądanym podziałom
        html_content = re.sub(
            r'<td[^>]*>', '<td style="page-break-inside:avoid !important;">', html_content)
        html_content = re.sub(
            r'<tr[^>]*>', '<tr style="page-break-inside:avoid !important;">', html_content)

        # Usuń wszystkie skrypty którę mogą modyfikować dokument
        html_content = re.sub(r'<script.*?</script>', '',
                              html_content, flags=re.DOTALL)

        # Zapisz zmodyfikowany HTML do pliku tymczasowego
        temp_html.write(html_content)
        temp_html_path = temp_html.name

    logger.info(f"Przetworzono HTML do tymczasowego pliku: {temp_html_path}")
    return temp_html_path


def calculate_optimal_height(html_file, item_count=None):
    """
    Oblicza optymalną wysokość PDF na podstawie zawartości HTML.

    Args:
        html_file (str): Ścieżka do pliku HTML
        item_count (int, optional): Liczba pozycji w dokumencie (jeśli znana)

    Returns:
        float: Optymalna wysokość w mm
    """
    try:
        # Jeśli nie podano liczby pozycji, próbujemy obliczyć ją z pliku HTML
        if item_count is None:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

                # Szukamy wszystkich wierszy tabeli (dla zamówień/faktur)
                # Różne podejścia zależnie od struktury HTML
                item_rows = re.findall(r'<tr class="item-name"', content)
                if item_rows:
                    item_count = len(item_rows)
                else:
                    # Próbujemy alternatywnego podejścia - liczymy <tr> w <tbody>
                    body_content = re.search(
                        r'<tbody>(.*?)</tbody>', content, re.DOTALL)
                    if body_content:
                        rows = re.findall(r'<tr', body_content.group(1))
                        # Zakładając że każdy element ma 2 wiersze
                        item_count = len(rows) // 2
                    else:
                        # Domyślnie zakładamy 10 pozycji jeśli nie możemy określić
                        item_count = 10

        logger.info(f"Wykryto {item_count} pozycji w dokumencie")

        # Obliczamy wysokość treści
        header_height_mm = 50  # Średni nagłówek dokumentu
        item_height_mm = 15  # Średnia wysokość pozycji
        footer_height_mm = 20  # Średnia stopka dokumentu

        # Całkowita wysokość treści
        total_content_height_mm = header_height_mm + \
            (item_height_mm * item_count) + footer_height_mm

        # Dodajemy margines bezpieczeństwa 5%
        optimal_height_mm = total_content_height_mm * 1.05

        logger.info(f"Obliczona optymalna wysokość: {optimal_height_mm:.2f}mm")
        return optimal_height_mm

    except Exception as e:
        logger.warning(f"Błąd podczas obliczania optymalnej wysokości: {e}")
        # Domyślna wysokość jeśli nie można obliczyć
        return 800  # Bezpieczna wartość dla większości dokumentów
