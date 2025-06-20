# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# zpl30cm.py

"""
Skrypt do drukowania testowych etykiet ZPL na drukarce termicznej Zebra.
Pozwala na wybór drukarki, rozdzielczości, szerokości i długości etykiet.
"""

import os
import sys
import time
import tempfile
import argparse
import subprocess

# Próba importu win32print dla drukowania w systemie Windows
try:
    import win32print

    WINDOWS_PRINTING = True
except ImportError:
    WINDOWS_PRINTING = False


def generuj_zpl_dla_etykiety(dlugosc_cm, dpi=300, szerokosc_cali=4):
    """
    Generuje kod ZPL dla testowej etykiety o określonej długości i szerokości.

    Args:
        dlugosc_cm (float): Długość etykiety w centymetrach
        dpi (int): Rozdzielczość drukarki w punktach na cal (DPI)
        szerokosc_cali (float): Szerokość etykiety w calach

    Returns:
        str: Wygenerowany kod ZPL
    """
    # Konwersja cm na punkty (dots) przy podanej rozdzielczości DPI
    # 1 cm = 10 mm, 1 cal = 25.4 mm, więc 1 cm = 10/25.4 cala
    # Przy podanym DPI, 1 cm = (10/25.4) * DPI punktów
    dlugosc_dots = round(dlugosc_cm * (10 / 25.4) * dpi)

    # Szerokość etykiety w punktach
    szerokosc_dots = round(szerokosc_cali * dpi)

    # Generowanie kodu ZPL
    zpl = []

    # Rozpoczęcie formatu ZPL
    zpl.append("^XA")

    # Resetowanie drukarki i ustawienie domyślnych parametrów
    zpl.append("^JA")

    # Ustaw szerokość etykiety
    zpl.append(f"^PW{szerokosc_dots}")

    # Ustawienie rozmiaru etykiety (długość)
    zpl.append(f"^LL{dlugosc_dots}")

    # Ustaw tryb odrywania (tear-off) zamiast cięcia
    zpl.append("^MMT")

    # Ustawienie typu nośnika
    zpl.append("^MTD")  # Typ materiału: termiczny direct

    # Ustaw początek układu współrzędnych
    zpl.append("^LH0,0")

    # Dodanie tekstów testowych
    zpl.append("^FO50,50^A0N,50,50^FDTest etykiety^FS")
    zpl.append(f"^FO50,120^A0N,40,40^FDDlugosc: {dlugosc_cm} cm^FS")
    zpl.append(f"^FO50,180^A0N,30,30^FD({dlugosc_dots} punktow, {dpi} DPI)^FS")
    zpl.append(f"^FO50,220^A0N,30,30^FDSzerokosc: {szerokosc_cali} cali^FS")

    # Dodanie linii na całej długości etykiety dla wizualizacji
    zpl.append(f"^FO30,270^GB{szerokosc_dots - 60},{max(dlugosc_dots - 320, 100)},3^FS")

    # Ilość kopii
    zpl.append("^PQ1")  # Drukuj 1 etykietę

    # Zakończenie formatu ZPL
    zpl.append("^XZ")

    return "\n".join(zpl)


def generuj_zpl_autokalibracja(dpi=300, szerokosc_cali=4):
    """
    Generuje kod ZPL dla kalibracji drukarki.

    Args:
        dpi (int): Rozdzielczość drukarki w punktach na cal (DPI)
        szerokosc_cali (float): Szerokość etykiety w calach

    Returns:
        str: Wygenerowany kod ZPL
    """
    # Szerokość etykiety w punktach
    szerokosc_dots = round(szerokosc_cali * dpi)

    # Generowanie kodu ZPL z autokonfiguracją
    zpl = []

    # Rozpoczęcie formatu ZPL
    zpl.append("^XA")

    # Resetowanie drukarki i ustawienie domyślnych parametrów
    zpl.append("^JA")

    # Ustaw szerokość etykiety
    zpl.append(f"^PW{szerokosc_dots}")

    # Autokalibracja
    zpl.append("^JUS")  # Wyczyszczenie i kalibracja czujników

    # Ustaw początek układu współrzędnych
    zpl.append("^LH0,0")

    # Ustaw tryb drukowania dla etykiet samoprzylepnych
    zpl.append("^MTD")  # Typ materiału: termiczny direct

    # Ustaw tryb odrywania
    zpl.append("^MMT")  # Tear-off mode

    # Dodaj tekst testowy
    zpl.append("^FO50,50^A0N,40,40^FDTest etykiet samoprzylepnych^FS")
    zpl.append("^FO50,100^A0N,30,30^FDAutomatyczna kalibracja^FS")
    zpl.append(f"^FO50,150^A0N,25,25^FDRozdzielczość: {dpi} DPI^FS")
    zpl.append(f"^FO50,180^A0N,25,25^FDSzerokość: {szerokosc_cali} cali ({szerokosc_dots} punktów)^FS")

    # Dodaj obramowanie
    zpl.append(f"^FO20,20^GB{szerokosc_dots - 40},230,3^FS")

    # Ilość kopii
    zpl.append("^PQ1")

    # Zakończenie formatu ZPL
    zpl.append("^XZ")

    return "\n".join(zpl)


def print_to_zebra(zpl_data, printer_name):
    """
    Wysyła dane ZPL do drukarki Zebra.

    Args:
        zpl_data (str): Dane ZPL do wydrukowania
        printer_name (str): Nazwa drukarki

    Returns:
        bool: True jeśli drukowanie powiodło się, False w przeciwnym wypadku
    """
    # Sprawdzanie, czy jesteśmy na Windows
    if sys.platform.startswith('win'):
        try:
            # Próba wydruku za pomocą systemu drukowania Windows
            if not WINDOWS_PRINTING:
                raise ImportError("win32print not available")

            # Uzyskaj domyślną drukarkę, jeśli nie określono
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()

            # Otwórz drukarkę
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                # Rozpocznij dokument
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("ZPL Document", None, "RAW"))
                try:
                    # Rozpocznij stronę
                    win32print.StartPagePrinter(hPrinter)
                    # Zapisz dane ZPL
                    win32print.WritePrinter(hPrinter, zpl_data.encode('utf-8'))
                    # Zakończ stronę
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    # Zakończ dokument
                    win32print.EndDocPrinter(hPrinter)
            finally:
                # Zamknij drukarkę
                win32print.ClosePrinter(hPrinter)

            print(f"Pomyślnie wysłano dane do drukarki {printer_name}")
            return True
        except ImportError:
            print("Moduł win32print nie znaleziony, używanie alternatywnej metody drukowania")
        except Exception as e:
            print(f"Błąd podczas korzystania z drukowania Windows: {e}")
            print("Używanie alternatywnej metody drukowania")

    # Alternatywna metoda drukowania (używanie komendy copy dla Windows)
    try:
        # Utworzenie tymczasowego pliku z kodem ZPL
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zpl')
        temp_file_name = temp_file.name

        # Zapisanie kodu ZPL do pliku (w trybie binarnym)
        with open(temp_file_name, 'wb') as f:
            f.write(zpl_data.encode('utf-8'))

        # Komenda do drukowania w Windows
        print_command = f'copy /b "{temp_file_name}" "{printer_name}"'
        print(f"Wykonuję komendę: {print_command}")
        subprocess.run(print_command, shell=True, check=True)

        print(f"Pomyślnie wysłano dane do drukarki {printer_name}")
        return True
    except Exception as e:
        print(f"Błąd wysyłania danych do drukarki: {e}")
        return False
    finally:
        # Usunięcie tymczasowego pliku
        try:
            # Krótkie opóźnienie przed usunięciem pliku
            time.sleep(1)
            os.unlink(temp_file_name)
        except Exception as e:
            print(f"Błąd podczas usuwania pliku tymczasowego: {e}")
            pass


def pobierz_liste_drukarek():
    """
    Pobiera listę dostępnych drukarek w systemie.

    Returns:
        list: Lista nazw drukarek
    """
    if WINDOWS_PRINTING:
        try:
            # Pobierz listę drukarek za pomocą win32print
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            return [printer[2] for printer in printers]
        except Exception as e:
            print(f"Błąd podczas pobierania listy drukarek: {e}")

    # Alternatywna metoda dla systemów bez win32print
    try:
        if sys.platform == 'win32':
            # Windows - użycie wmic
            result = subprocess.run('wmic printer get name', shell=True, capture_output=True, text=True, check=True)
            # Przetworzenie listy drukarek
            drukarki = [line.strip() for line in result.stdout.split('\n') if line.strip() and line.strip() != 'Name']
            return drukarki
        else:
            # Linux/Mac - użycie lpstat
            result = subprocess.run('lpstat -a', shell=True, capture_output=True, text=True, check=True)
            # Przetworzenie listy drukarek
            drukarki = [line.split()[0] for line in result.stdout.split('\n') if line.strip()]
            return drukarki
    except Exception as e:
        print(f"Błąd podczas pobierania listy drukarek: {e}")
        return []


def main():
    """
    Główna funkcja programu.
    """
    parser = argparse.ArgumentParser(description='Drukowanie testowych etykiet ZPL na drukarce termicznej')
    parser.add_argument('printer_name', nargs='?', help='Nazwa drukarki (domyślnie: wybór z listy)')
    parser.add_argument('--list', '-l', action='store_true', help='Wyświetl listę dostępnych drukarek')
    parser.add_argument('--length', '-d', type=float, help='Długość etykiety w cm (domyślnie: 5, 15, 30)')
    parser.add_argument('--save', '-s', action='store_true', help='Zapisz kod ZPL do pliku')
    parser.add_argument('--interactive', '-i', action='store_true', help='Tryb interaktywny z wyborem drukarki')
    parser.add_argument('--dpi', type=int, default=300, help='Rozdzielczość drukarki w DPI (domyślnie: 300)')
    parser.add_argument('--width', '-w', type=float, default=4.0, help='Szerokość etykiety w calach (domyślnie: 4.0)')
    parser.add_argument('--calibration', '-c', action='store_true', help='Drukuj etykietę kalibracyjną')
    args = parser.parse_args()

    # Pobierz listę drukarek
    drukarki = pobierz_liste_drukarek()

    # Wyświetl listę drukarek, jeśli zażądano
    if args.list:
        if drukarki:
            print("Dostępne drukarki:")
            for i, drukarka in enumerate(drukarki, 1):
                print(f"{i}. {drukarka}")
            if WINDOWS_PRINTING:
                print(f"Domyślna drukarka: {win32print.GetDefaultPrinter()}")
        else:
            print("Nie znaleziono drukarek.")
        return

    # Wybór drukarki
    printer_name = args.printer_name

    # Jeśli nie podano drukarki lub wybrano tryb interaktywny, daj użytkownikowi możliwość wyboru
    if not printer_name or args.interactive:
        if drukarki:
            print("Dostępne drukarki:")
            for i, drukarka in enumerate(drukarki, 1):
                print(f"{i}. {drukarka}")

            wybor = input("\nWybierz numer drukarki lub wpisz jej nazwę [1]: ")

            if not wybor:
                # Domyślnie pierwsza drukarka
                printer_name = drukarki[0]
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
            if not printer_name:
                printer_name = input("Nie znaleziono drukarek. Wpisz nazwę drukarki ręcznie: ")
                if not printer_name:
                    printer_name = "ZDesigner GK420d"  # Domyślna drukarka, jeśli nic nie wpisano

    if not printer_name:
        printer_name = "ZDesigner GK420d"  # Domyślna drukarka, jeśli wszystko inne zawiodło

    # Pytanie o rozdzielczość DPI w trybie interaktywnym
    dpi = args.dpi
    if args.interactive:
        dpi_input = input(f"\nPodaj rozdzielczość drukarki w DPI [{dpi}]: ")
        if dpi_input:
            try:
                dpi = int(dpi_input)
            except ValueError:
                print(f"Nieprawidłowa wartość, używam domyślnej rozdzielczości {dpi} DPI")

    # Pytanie o szerokość etykiety w trybie interaktywnym
    szerokosc_cali = args.width
    if args.interactive:
        szerokosc_input = input(f"\nPodaj szerokość etykiety w calach [{szerokosc_cali}]: ")
        if szerokosc_input:
            try:
                szerokosc_cali = float(szerokosc_input)
            except ValueError:
                print(f"Nieprawidłowa wartość, używam domyślnej szerokości {szerokosc_cali} cali")

    # Wybór długości etykiety lub kalibracji w trybie interaktywnym
    if args.interactive and not args.length and not args.calibration:
        print("\nWybierz opcję drukowania:")
        print("1. Drukuj standardowe etykiety testowe (5, 15, 30 cm)")
        print("2. Drukuj jedną etykietę o określonej długości")
        print("3. Drukuj etykietę kalibracyjną")

        wybor_opcji = input("Wybierz opcję [1]: ")

        if wybor_opcji == "2":
            dlugosc_input = input("Podaj długość etykiety w cm [10]: ")
            if dlugosc_input:
                try:
                    args.length = float(dlugosc_input)
                except ValueError:
                    print("Nieprawidłowa wartość, używam domyślnej długości 10 cm")
                    args.length = 10.0
            else:
                args.length = 10.0
        elif wybor_opcji == "3":
            args.calibration = True

    # Pytanie o zapis do pliku w trybie interaktywnym
    if args.interactive and not args.save:
        zapis = input("Czy zapisać kod ZPL do pliku? (t/n) [n]: ")
        if zapis.lower() in ('t', 'tak'):
            args.save = True

    # Potwierdzenie przed drukowaniem
    if args.interactive:
        if args.calibration:
            potwierdzenie = input(
                f"\nDrukuję etykietę kalibracyjną na drukarce '{printer_name}' ({dpi} DPI, {szerokosc_cali} cali). Kontynuować? (t/n) [t]: ")
        elif args.length:
            potwierdzenie = input(
                f"\nDrukuję etykietę o długości {args.length} cm na drukarce '{printer_name}' ({dpi} DPI, {szerokosc_cali} cali). Kontynuować? (t/n) [t]: ")
        else:
            potwierdzenie = input(
                f"\nDrukuję standardowe etykiety testowe (5, 15, 30 cm) na drukarce '{printer_name}' ({dpi} DPI, {szerokosc_cali} cali). Kontynuować? (t/n) [t]: ")

        if potwierdzenie and potwierdzenie.lower() not in ('t', 'tak'):
            print("Drukowanie anulowane.")
            return

    # Drukowanie etykiety kalibracyjnej
    if args.calibration:
        zpl_data = generuj_zpl_autokalibracja(dpi, szerokosc_cali)
        print(f"Drukuję etykietę kalibracyjną na drukarce {printer_name} ({dpi} DPI, {szerokosc_cali} cali)")

        # Zapisz kod ZPL do pliku, jeśli zażądano
        if args.save:
            output_file = f"etykieta_kalibracyjna_{dpi}dpi_{szerokosc_cali}cali.zpl"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(zpl_data)
            print(f"Kod ZPL zapisano do pliku {output_file}")

        # Wydrukuj etykietę
        print_to_zebra(zpl_data, printer_name)
    # Jeśli podano długość etykiety, wydrukuj tylko jedną etykietę
    elif args.length:
        zpl_data = generuj_zpl_dla_etykiety(args.length, dpi, szerokosc_cali)
        print(
            f"Drukuję etykietę o długości {args.length} cm na drukarce {printer_name} ({dpi} DPI, {szerokosc_cali} cali)")

        # Zapisz kod ZPL do pliku, jeśli zażądano
        if args.save:
            output_file = f"etykieta_{args.length}cm_{dpi}dpi_{szerokosc_cali}cali.zpl"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(zpl_data)
            print(f"Kod ZPL zapisano do pliku {output_file}")

        # Wydrukuj etykietę
        print_to_zebra(zpl_data, printer_name)
    else:
        # Wydrukuj standardowe etykiety testowe
        test_dlugosci = [5, 15, 30]  # długości w cm

        print(
            f"Drukuję testowe etykiety o długościach {', '.join(map(str, test_dlugosci))} cm na drukarce {printer_name} ({dpi} DPI, {szerokosc_cali} cali)")

        for i, dlugosc in enumerate(test_dlugosci):
            zpl_data = generuj_zpl_dla_etykiety(dlugosc, dpi, szerokosc_cali)
            print(f"\nDrukuję etykietę {i + 1}/{len(test_dlugosci)}: {dlugosc} cm")

            # Zapisz kod ZPL do pliku, jeśli zażądano
            if args.save:
                output_file = f"etykieta_{dlugosc}cm_{dpi}dpi_{szerokosc_cali}cali.zpl"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(zpl_data)
                print(f"Kod ZPL zapisano do pliku {output_file}")

            # Wydrukuj etykietę
            print_to_zebra(zpl_data, printer_name)

            # Krótka pauza między wydrukami
            if i < len(test_dlugosci) - 1:
                print("Pauza 2 sekundy przed następnym wydrukiem...")
                time.sleep(2)

        print("\nWszystkie etykiety zostały wysłane do drukowania!")
        print("UWAGA: Ta drukarka nie ma gilotyny. Etykiety należy oderwać ręcznie.")


if __name__ == '__main__':
    # Obsługa braku parametrów - uruchomienie w trybie interaktywnym
    if len(sys.argv) == 1:
        sys.argv.append('-i')  # Dodaj flagę trybu interaktywnego

    main()

#python zpl30cm.py "ZDesigner GK420d"
#python python-thermal-zpl.py "ZDesigner GK420d" --dpi 203 --length 10 --save