#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funkcja do generowania plików PDF z dokumentów ZO.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)

def generate_pdf(document_data, output_path):
    """
    Generuje plik PDF z danymi dokumentu ZO.

    Args:
        document_data (dict): Dane dokumentu ZO
        output_path (str): Ścieżka do zapisania pliku PDF

    Returns:
        bool: True jeśli generowanie się powiodło, False w przeciwnym razie
    """
    try:
        # Upewnij się, że katalog docelowy istnieje
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Tworzenie dokumentu PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Przygotowanie stylów
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        # Elementy dokumentu
        elements = []

        # Tytuł dokumentu
        elements.append(Paragraph(f"Zamówienie Odbiorcy: {document_data['numer_dokumentu']}", title_style))
        elements.append(Spacer(1, 12))

        # Dane podstawowe
        data = [
            ["Data dokumentu:", document_data['data_dokumentu']],
            ["Kontrahent:", document_data['kontrahent']],
            ["Wartość netto:", f"{document_data['wartosc_netto']:.2f} PLN"],
            ["Wartość brutto:", f"{document_data['wartosc_brutto']:.2f} PLN"]
        ]

        if document_data.get('uwagi'):
            data.append(["Uwagi:", document_data['uwagi']])

        if document_data.get('odebral'):
            data.append(["Odebrał:", document_data['odebral']])

        # Tworzenie tabeli z danymi
        table = Table(data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        # Generowanie dokumentu
        doc.build(elements)

        logger.info(f"Wygenerowano PDF dla dokumentu {document_data['numer_dokumentu']} w {output_path}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas generowania PDF: {e}")
        return False
