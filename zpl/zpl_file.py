#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zawierający funkcje do walidacji i naprawy plików ZPL.
Uzupełnienie do modułu zpl_printer.py.
"""

import re
import os
import logging

# Konfiguracja loggera
logger = logging.getLogger("zpl_validator")


def validate_zpl_file(zpl_file, return_content=False):
    """
    Analizuje plik ZPL i sygnalizuje wykryte nieprawidłowości.

    Args:
        zpl_file (str): Ścieżka do pliku ZPL
        return_content (bool, optional): Czy zwrócić zawartość pliku. Domyślnie False.

    Returns:
        dict: Słownik zawierający informacje o statusie walidacji:
            - success (bool): Czy walidacja zakończyła się bez krytycznych błędów
            - issues (list): Lista wykrytych problemów
            - label_count (int): Liczba etykiet w pliku
            - content (str, optional): Zawartość pliku (jeśli return_content=True)
    """
    issues = []

    try:
        # Odczytaj plik ZPL
        try:
            with open(zpl_file, 'r', encoding='utf-8') as file:
                zpl_code = file.read()
        except UnicodeDecodeError:
            # Alternatywne kodowanie, jeśli UTF-8 zawiedzie
            with open(zpl_file, 'r', encoding='latin-1') as file:
                zpl_code = file.read()
                issues.append({
                    'type': 'warning',
                    'message': 'Plik nie jest zakodowany w UTF-8, użyto kodowania latin-1'
                })

        # Sprawdź czy plik nie jest pusty
        if not zpl_code or zpl_code.strip() == '':
            issues.append({
                'type': 'error',
                'message': 'Pusty plik ZPL'
            })
            result = {
                'success': False,
                'issues': issues,
                'label_count': 0
            }
            if return_content:
                result['content'] = zpl_code
            return result

        # Znajdź wszystkie etykiety (pary ^XA...^XZ)
        label_pairs = re.findall(r'\^XA.*?\^XZ', zpl_code, re.DOTALL)
        label_count = len(label_pairs)

        # Sprawdź liczbę etykiet
        if label_count == 0:
            start_tags = zpl_code.count('^XA')
            end_tags = zpl_code.count('^XZ')

            if start_tags == 0 and end_tags == 0:
                issues.append({
                    'type': 'error',
                    'message': 'Brak znaczników etykiety (^XA i ^XZ)'
                })
            elif start_tags > 0 and end_tags == 0:
                issues.append({
                    'type': 'error',
                    'message': f'Znaleziono {start_tags} początkowych znaczników ^XA, ale brak końcowych ^XZ'
                })
            elif start_tags == 0 and end_tags > 0:
                issues.append({
                    'type': 'error',
                    'message': f'Znaleziono {end_tags} końcowych znaczników ^XZ, ale brak początkowych ^XA'
                })
            else:
                issues.append({
                    'type': 'error',
                    'message': f'Znaleziono {start_tags} początkowych ^XA i {end_tags} końcowych ^XZ, ale nie tworzą one kompletnych etykiet'
                })
        elif label_count > 1:
            issues.append({
                'type': 'warning',
                'message': f'Plik zawiera {label_count} etykiet, co może prowadzić do wielokrotnych wydruków'
            })

        # Sprawdź, czy istnieją fragmenty ZPL poza etykietami
        total_label_length = sum(len(label) for label in label_pairs)
        if total_label_length < len(zpl_code.strip()):
            issues.append({
                'type': 'warning',
                'message': 'Kod ZPL zawiera fragmenty poza etykietami (^XA...^XZ)'
            })

        # Sprawdź inne typowe problemy
        if '^PR' not in zpl_code:
            issues.append({
                'type': 'info',
                'message': 'Brak ustawienia prędkości drukowania (^PR)'
            })

        if '^FS' in zpl_code and not re.search(r'\^FO.*?\^FS', zpl_code, re.DOTALL):
            issues.append({
                'type': 'warning',
                'message': 'Znaleziono polecenie ^FS bez odpowiadającego ^FO (pozycjonowanie pola)'
            })

        # Zlicz wystąpienia innych kluczowych komend
        field_count = zpl_code.count('^FD')
        if field_count == 0:
            issues.append({
                'type': 'warning',
                'message': 'Brak pól danych (^FD) w etykiecie'
            })

        # Sukces walidacji, jeśli nie ma krytycznych błędów
        success = not any(issue['type'] == 'error' for issue in issues)

        result = {
            'success': success,
            'issues': issues,
            'label_count': label_count
        }

        if return_content:
            result['content'] = zpl_code

        return result

    except FileNotFoundError:
        return {
            'success': False,
            'issues': [{
                'type': 'error',
                'message': f'Nie znaleziono pliku: {zpl_file}'
            }],
            'label_count': 0
        }
    except Exception as e:
        logger.exception(f"Nieoczekiwany błąd podczas walidacji ZPL: {e}")
        return {
            'success': False,
            'issues': [{
                'type': 'error',
                'message': f'Nieoczekiwany błąd podczas walidacji: {str(e)}'
            }],
            'label_count': 0
        }


def repair_zpl_file(zpl_file, output_file=None, backup=True):
    """
    Naprawia typowe problemy w pliku ZPL i zapisuje poprawioną wersję.

    Args:
        zpl_file (str): Ścieżka do pliku ZPL do naprawy
        output_file (str, optional): Ścieżka do pliku wyjściowego. Jeśli None,
                                    nadpisuje plik wejściowy.
        backup (bool, optional): Czy utworzyć kopię zapasową oryginalnego pliku. Domyślnie True.

    Returns:
        dict: Słownik zawierający informacje o statusie naprawy:
            - success (bool): Czy naprawa zakończyła się powodzeniem
            - message (str): Komunikat o statusie operacji
            - fixed_issues (list): Lista naprawionych problemów
            - output_file (str): Ścieżka do naprawionego pliku
    """
    # Najpierw przeprowadzamy walidację
    validation_result = validate_zpl_file(zpl_file, return_content=True)

    if not validation_result['success'] and 'content' not in validation_result:
        return {
            'success': False,
            'message': 'Nie można naprawić pliku - błąd odczytu',
            'fixed_issues': [],
            'output_file': None
        }

    zpl_code = validation_result.get('content', '')
    fixed_issues = []

    # Sprawdź czy mamy co naprawiać
    if validation_result['success'] and not validation_result['issues']:
        return {
            'success': True,
            'message': 'Plik jest poprawny, naprawa nie jest wymagana',
            'fixed_issues': [],
            'output_file': zpl_file
        }

    # Określenie pliku wyjściowego
    if output_file is None:
        output_file = zpl_file

    # Wykonaj kopię zapasową jeśli potrzeba
    if backup and output_file == zpl_file:
        backup_file = f"{zpl_file}.bak"
        try:
            with open(zpl_file, 'rb') as src, open(backup_file, 'wb') as dst:
                dst.write(src.read())
            logger.info(f"Utworzono kopię zapasową: {backup_file}")
        except Exception as e:
            logger.warning(f"Nie udało się utworzyć kopii zapasowej: {e}")

    # Napraw znalezione problemy

    # 1. Sprawdź i napraw wielokrotne etykiety
    if validation_result['label_count'] > 1:
        # Znajdź pierwszą kompletną etykietę
        match = re.search(r'\^XA.*?\^XZ', zpl_code, re.DOTALL)
        if match:
            zpl_code = match.group(0)
            fixed_issues.append(
                f'Usunięto dodatkowe etykiety, pozostawiono tylko pierwszą'
            )

    # 2. Dodaj znaczniki etykiety, jeśli ich brak
    start_fixed = False
    end_fixed = False

    if not zpl_code.strip().startswith('^XA'):
        zpl_code = '^XA\n' + zpl_code.strip()
        start_fixed = True

    if not zpl_code.strip().endswith('^XZ'):
        zpl_code = zpl_code.strip() + '\n^XZ'
        end_fixed = True

    if start_fixed and end_fixed:
        fixed_issues.append('Dodano brakujące znaczniki etykiety ^XA i ^XZ')
    elif start_fixed:
        fixed_issues.append('Dodano brakujący znacznik początku etykiety ^XA')
    elif end_fixed:
        fixed_issues.append('Dodano brakujący znacznik końca etykiety ^XZ')

    # 3. Usuń fragmenty poza etykietami
    if not start_fixed and not end_fixed and validation_result['label_count'] > 0:
        cleaned_zpl = ''
        in_label = False

        for line in zpl_code.splitlines():
            if '^XA' in line:
                in_label = True
                cleaned_zpl += line + '\n'
            elif '^XZ' in line:
                in_label = False
                cleaned_zpl += line + '\n'
            elif in_label:
                cleaned_zpl += line + '\n'

        if cleaned_zpl != zpl_code:
            zpl_code = cleaned_zpl
            fixed_issues.append(
                'Usunięto kod ZPL znajdujący się poza etykietami')

    # 4. Dodaj domyślne ustawienia prędkości jeśli brak
    if '^PR' not in zpl_code:
        # Dodaj po ^XA
        zpl_code = zpl_code.replace('^XA', '^XA\n^PR3')
        fixed_issues.append(
            'Dodano domyślne ustawienie prędkości drukowania (^PR3)')

    # Zapisz naprawiony plik
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(zpl_code)

        success_msg = f"Pomyślnie naprawiono plik ZPL: {output_file}"
        if not fixed_issues:
            success_msg = f"Nie wykryto problemów wymagających naprawy w pliku ZPL"

        return {
            'success': True,
            'message': success_msg,
            'fixed_issues': fixed_issues,
            'output_file': output_file
        }
    except Exception as e:
        error_msg = f"Błąd podczas zapisywania naprawionego pliku: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'message': error_msg,
            'fixed_issues': fixed_issues,
            'output_file': None
        }
