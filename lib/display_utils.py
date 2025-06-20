#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funkcje pomocnicze do wyświetlania danych.
"""

from tabulate import tabulate
from lib import format_date, format_number

def display_documents(documents):
    """Wyświetla dokumenty w formie tabeli"""
    if not documents:
        print("\nNie znaleziono żadnych dokumentów ZO.")
        return

    # Przygotowanie danych do wyświetlenia
    table_data = []
    for i, doc in enumerate(documents, 1):
        table_data.append([
            i,
            doc['numer_dokumentu'],
            format_date(doc['data_dokumentu']),
            doc['kontrahent'],
            format_number(doc['wartosc_netto']),
            doc['uwagi'] or '',
            doc['odebral'] or ''
        ])

    # Nagłówki kolumn
    headers = [
        'Nr',
        'Numer',
        'Data',
        'Kontrahent',
        'Wartość netto',
        'Uwagi',
        'Odebrał'
    ]

    # Wyświetlenie tabeli
    print("\nDokumenty ZO w systemie:")
    print(tabulate(
        table_data,
        headers=headers,
        tablefmt='grid',
        numalign='right',
        stralign='left'
    ))

    return documents

def get_document_by_index(documents, choice):
    """Pobiera dokument o podanym indeksie lub numerze"""
    try:
        # Sprawdzenie czy podano numer dokumentu
        if choice.startswith('ZO'):
            for doc in documents:
                if doc['numer_dokumentu'] == choice:
                    return doc
            return None

        # Jeśli nie, próbujemy użyć jako indeksu
        idx = int(choice) - 1
        if 0 <= idx < len(documents):
            return documents[idx]
        return None
    except ValueError:
        return None
