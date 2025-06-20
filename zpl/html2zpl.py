#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# html2zpl.py

"""
Skrypt do konwersji dokumentów HTML (w tym faktur/zamówień z tabelami) do formatu ZPL
i drukowania ich na drukarkach etykiet Zebra.
"""

import os
import sys
import argparse
import logging
from zpl.zpl_utils import *
from zpl.zpl_printer import *

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('html2zpl.log'),
        logging.StreamHandler()
    ]
)

def main():
    """
    Główna funkcja programu.
    """
    parser = argparse.ArgumentParser(description='Konwersja i drukowanie HTML na drukarkach Zebra (ZPL)')
    parser.add_argument('file_path', nargs='?', help='Ścieżka do pliku HTML (domyślnie: wybór z listy)')
    parser.add_argument('--list', '-l', action='store_true', help='Wyświetl listę dostępnych drukarek')
    parser.add_argument('--printer', '-p', help='Nazwa drukarki (domyślnie: wybór z listy)')
    parser.add_argument('--save', '-s', action='store_true', help='Zapisz kod ZPL do pliku')
    parser.add_argument('--interactive', '-i', action='store_true', help='Tryb interaktywny z wyborem parametrów')
    parser.add_argument('--dpi', type=int, default=203, help='Rozdzielczość drukarki w DPI (domyślnie: 203)')
    parser.add_argument('--width', '-w', type=float, default=4.0, help='Szerokość etykiety w calach (domyślnie: 4.0)')
    parser.add_argument('--height', type=float, default=0, help='Wysokość etykiety w calach (domyślnie: 0 - auto)')
    parser.add_argument('--encode', '-e', default='utf8', help='Kodowanie znaków (domyślnie: cp852)')
    parser.add_argument('--output', '-o', help='Ścieżka do pliku wyjściowego ZPL (domyślnie: auto)')
    args = parser.parse_args()

    # Pobierz listę drukarek
    drukarki = get_available_printers()

    # Wyświetl listę drukarek, jeśli zażądano
    if args.list:
        if drukarki:
            print("Dostępne drukarki:")
            for i, drukarka in enumerate(drukarki, 1):
                print(f"{i}. {drukarka}")
        else:
            print("Nie znaleziono drukarek.")
        return

    # Tryb interaktywny
    if args.interactive or (not args.file_path and not args.printer):
        # Wybór pliku HTML
        if not args.file_path:
            file_path = input("Podaj ścieżkę do pliku HTML: ")
            if not file_path:
                print("Nie podano pliku HTML. Kończenie.")
                return
        else:
            file_path = args.file_path

        # Wybór drukarki
        if not args.printer:
            if drukarki:
                print("Dostępne drukarki:")
                for i, drukarka in enumerate(drukarki, 1):
                    print(f"{i}. {drukarka}")
                wybor = input("\nWybierz numer drukarki lub wpisz jej nazwę [1]: ")
                if not wybor:
                    printer_name = drukarki[0] if drukarki else None
                else:
                    try:
                        indeks = int(wybor) - 1
                        if 0 <= indeks < len(drukarki):
                            printer_name = drukarki[indeks]
                        else:
                            printer_name = wybor
                    except ValueError:
                        printer_name = wybor
            else:
                printer_name = input("Nie znaleziono drukarek. Wpisz nazwę drukarki ręcznie: ")
        else:
            printer_name = args.printer

        # Parametry drukowania
        dpi_input = input(f"Podaj rozdzielczość drukarki w DPI [{args.dpi}]: ")
        dpi = int(dpi_input) if dpi_input else args.dpi

        width_input = input(f"Podaj szerokość etykiety w calach [{args.width}]: ")
        width = float(width_input) if width_input else args.width

        height_input = input(f"Podaj wysokość etykiety w calach (0 dla auto) [{args.height}]: ")
        height = float(height_input) if height_input else args.height

        encode_input = input(f"Podaj kodowanie znaków [{args.encode}]: ")
        encode = encode_input if encode_input else args.encode

        save_input = input("Czy zapisać kod ZPL do pliku? (t/n) [n]: ")
        save_zpl = save_input.lower() in ('t', 'tak')

        if save_zpl:
            output_file = input("Podaj ścieżkę do pliku wyjściowego ZPL (Enter dla auto): ")
            if not output_file:
                output_file = os.path.splitext(file_path)[0] + ".zpl"
        else:
            output_file = None

        # Drukowanie
        print_html_from_file(
            file_path=file_path,
            printer_name=printer_name,
            dpi=dpi,
            label_width=width,
            label_height=height,
            encoding=encode,
            save_zpl=save_zpl,
            output_file=output_file,
            interactive=True
        )
    else:
        # Tryb nieinteraktywny
        print_html_from_file(
            file_path=args.file_path,
            printer_name=args.printer,
            dpi=args.dpi,
            label_width=args.width,
            label_height=args.height,
            encoding=args.encode,
            save_zpl=args.save,
            output_file=args.output
        )

if __name__ == '__main__':
    # Obsługa braku parametrów - uruchomienie w trybie interaktywnym
    if len(sys.argv) == 1:
        sys.argv.append('-i')  # Dodaj flagę trybu interaktywnego

    main()