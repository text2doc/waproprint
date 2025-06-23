#!/usr/bin/env python
# -*- coding: utf-8 -*-
# zpl_printer.py

"""
Moduł do obsługi drukowania plików ZPL na drukarkach sieciowych.
Bazuje na kodzie z printerlan.py, zintegrowany z systemem konfiguracji z sql2html.py.
"""

import os
import sys
import socket
import logging
from lib.ConfigManager import ConfigManager

# Konfiguracja loggera
logger = logging.getLogger("zpl_printer")


def print_zpl_to_network_printer(zpl_file, printer_ip=None, port=None, config=None):
    """
    Wyślij plik ZPL do drukarki sieciowej przez bezpośrednie połączenie socket.
    Pobiera parametry z config.ini jeśli nie są podane explicite.

    Args:
        zpl_file (str): Ścieżka do pliku ZPL
        printer_ip (str, optional): Adres IP drukarki. Jeśli None, pobierane z konfiguracji.
        port (int, optional): Port drukarki. Jeśli None, pobierane z konfiguracji.
        config (ConfigManager, optional): Obiekt konfiguracyjny. Jeśli None, tworzy nowy.

    Returns:
        dict: Słownik zawierający informację o statusie operacji
    """
    try:
        # Inicjalizacja konfiguracji, jeśli nie została podana
        if config is None:
            config = ConfigManager()
            config.load_config()

        # Pobierz parametry z konfiguracji jeśli nie zostały podane
        if printer_ip is None:
            printer_ip = config.get_thermal_printer_ip()
            if not printer_ip:
                error_msg = "Nie znaleziono adresu IP drukarki w konfiguracji"
                logger.error(error_msg)
                return {'success': False, 'message': error_msg, 'status': 'error'}

        if port is None:
            port = config.get_thermal_printer_port()
            if not port:
                port = 9100  # Domyślny port dla drukarek Zebra
                logger.info(
                    f"Nie znaleziono portu drukarki w konfiguracji, używam domyślnego: {port}")

        # Odczytaj plik ZPL
        try:
            with open(zpl_file, 'r', encoding='utf-8') as file:
                zpl_code = file.read()
        except UnicodeDecodeError:
            # Alternatywne kodowanie, jeśli UTF-8 zawiedzie
            with open(zpl_file, 'r', encoding='latin-1') as file:
                zpl_code = file.read()

        # Walidacja kodu ZPL
        if not zpl_code:
            error_msg = f"Błąd: Pusty plik ZPL {zpl_file}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg, 'status': 'error'}

        # Upewnij się, że kod ZPL rozpoczyna się i kończy poprawnie
        if not zpl_code.startswith('^XA'):
            zpl_code = '^XA' + zpl_code
        if not zpl_code.endswith('^XZ'):
            zpl_code += '^XZ'

        # Informacje debugowe
        logger.info(f"Szczegóły pliku ZPL: {zpl_file}")
        logger.info(f"Rozmiar pliku: {len(zpl_code)} znaków")
        logger.debug(f"Pierwsze 200 znaków: {zpl_code[:200]}")

        # Utwórz połączenie socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Ustaw timeout aby zapobiec zawieszeniu
            s.settimeout(10)

            # Połącz z drukarką
            try:
                logger.info(
                    f"Łączenie z drukarką na adresie {printer_ip}:{port}...")
                s.connect((printer_ip, port))
            except socket.error as e:
                error_msg = f"Błąd połączenia: {e}"
                logger.error(error_msg)
                logger.error("Możliwe przyczyny:")
                logger.error("- Niepoprawny adres IP")
                logger.error("- Drukarka wyłączona")
                logger.error("- Problem z połączeniem sieciowym")
                return {'success': False, 'message': error_msg, 'status': 'error'}

            # Wyślij kod ZPL
            try:
                s.sendall(zpl_code.encode('utf-8'))
                success_msg = f"Pomyślnie wysłano plik ZPL do drukarki na adresie {printer_ip}"
                logger.info(success_msg)
                return {'success': True, 'message': success_msg, 'status': 'printed'}
            except socket.error as e:
                error_msg = f"Błąd podczas wysyłania danych: {e}"
                logger.error(error_msg)
                return {'success': False, 'message': error_msg, 'status': 'error'}

    except FileNotFoundError:
        error_msg = f"Błąd: Nie znaleziono pliku ZPL: {zpl_file}"
        logger.error(error_msg)
        logger.error("Możliwe przyczyny:")
        logger.error("- Niepoprawna ścieżka pliku")
        logger.error("- Plik został przeniesiony lub usunięty")
        logger.error(f"Bieżący katalog roboczy: {os.getcwd()}")
        logger.error(f"Pliki w bieżącym katalogu: {os.listdir()}")
        return {'success': False, 'message': error_msg, 'status': 'error'}
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd: {e}"
        logger.exception(error_msg)
        return {'success': False, 'message': error_msg, 'status': 'error'}


def list_zpl_files(directory=None, config=None):
    """
    Wylistuj wszystkie pliki ZPL w katalogu. Używa ścieżki z konfiguracji, jeśli nie podano.

    Args:
        directory (str, optional): Katalog do przeszukania. Domyślnie używa katalogu z konfiguracji.
        config (ConfigManager, optional): Obiekt konfiguracyjny. Jeśli None, tworzy nowy.

    Returns:
        list: Lista ścieżek do plików ZPL
    """
    try:
        # Inicjalizacja konfiguracji, jeśli nie została podana
        if config is None:
            config = ConfigManager()
            config.load_config()

        # Użyj katalogu z konfiguracji, jeśli nie podano
        if directory is None:
            directory = config.get_zo_zpl_dir()
            if not directory:
                logger.warning(
                    "Nie znaleziono ścieżki katalogu ZPL w konfiguracji, używam bieżącego katalogu")
                directory = '.'

        # Upewnij się, że katalog istnieje
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Utworzono katalog ZPL: {directory}")

        # Znajdź pliki ZPL
        zpl_files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith('.zpl')
        ]

        logger.info(
            f"Znaleziono {len(zpl_files)} plików ZPL w katalogu {directory}")
        return zpl_files

    except Exception as e:
        logger.exception(f"Błąd podczas listowania plików ZPL: {e}")
        return []
