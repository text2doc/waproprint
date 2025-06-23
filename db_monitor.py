#!/usr/bin/env python
# -*- coding: utf-8 -*-
# db_monitor.py

"""
Skrypt monitorujący bazę danych SQL Server i automatycznie drukujący dokumenty ZO.
Monitoruje co 5 sekund nowe dokumenty i generuje wydruki PDF.
"""

import sys
import os
import subprocess
from pathlib import Path
import logging
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import locale
import win32api
import win32con
import win32security
import ntsecuritycon as con
import traceback
from db_monitor_service import DBMonitorService

# Pobierz ścieżkę do katalogu skryptu
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ustawienie kodowania dla konsoli Windows
if sys.platform == 'win32':
    # Ustawienie kodowania dla konsoli Windows
    if sys.stdout.encoding != 'cp1250':
        sys.stdout.reconfigure(encoding='cp1250')
    if sys.stderr.encoding != 'cp1250':
        sys.stderr.reconfigure(encoding='cp1250')
    # Ustawienie locale dla Windows
    locale.setlocale(locale.LC_ALL, 'Polish_Poland.1250')

    # Wymuszenie kodowania dla konsoli Windows
    os.system('chcp 1250 > nul')

# Konfiguracja loggera
log_file = os.path.join(SCRIPT_DIR, 'db_monitor.log')
console_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(log_file, encoding='cp1250', mode='a')

# Formatowanie logów
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Konfiguracja głównego loggera
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Wyczyść domyślne handlery, jeśli były skonfigurowane wcześniej
logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
if root_logger.handlers:
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)


def show_logs():
    """Wyświetla zawartość plików logów."""
    # Wyświetl logi db_monitor.log
    if os.path.exists(log_file):
        print("\n=== Logi db_monitor.log ===")
        try:
            with open(log_file, 'r', encoding='cp1250') as f:
                print(f.read())
        except Exception as e:
            print(f"Błąd podczas odczytu pliku logów: {e}")
    else:
        print("\nPlik db_monitor.log nie istnieje")

    # Wyświetl logi sql2html.log
    sql2html_log = os.path.join(SCRIPT_DIR, 'sql2html.log')
    if os.path.exists(sql2html_log):
        print("\n=== Logi sql2html.log ===")
        try:
            with open(sql2html_log, 'r', encoding='cp1250') as f:
                print(f.read())
        except Exception as e:
            print(f"Błąd podczas odczytu pliku logów: {e}")
    else:
        print("\nPlik sql2html.log nie istnieje")


def run_direct():
    """Uruchamia skrypt sql2html.py bezpośrednio dla testów."""
    try:
        logger.info("Bezpośrednie uruchomienie sql2html.py...")
        sql2html_path = os.path.join(SCRIPT_DIR, 'sql2html.py')

        if not os.path.exists(sql2html_path):
            logger.error(
                f"Nie znaleziono pliku sql2html.py w ścieżce: {sql2html_path}")
            return False

        # Uruchom skrypt bezpośrednio
        python_exe = sys.executable
        cmd = [python_exe, sql2html_path]

        logger.info(f"Uruchamiam komendę: {' '.join(cmd)}")

        # Ustaw zmienne środowiskowe
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'cp1250'

        # Uruchom w podprocesie z poprawnym kodowaniem
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SCRIPT_DIR,
            text=True,
            encoding='cp1250',
            errors='replace'
        )

        stdout, stderr = process.communicate()

        logger.info(f"Kod wyjścia: {process.returncode}")

        # Przetwórz wyjście z poprawnym kodowaniem
        if stdout:
            logger.info(f"Standardowe wyjście: {stdout}")

        if stderr:
            logger.error(f"Błędy: {stderr}")

        return process.returncode == 0
    except Exception as e:
        logger.error(
            f"Błąd podczas bezpośredniego uruchamiania: {e}", exc_info=True)
        return False


def repair_service():
    """Funkcja do naprawy usługi - zatrzymuje, usuwa i ponownie instaluje."""
    try:
        logger.info("Rozpoczynam naprawę usługi...")

        # 1. Spróbuj zatrzymać usługę
        try:
            logger.info("Próbuję zatrzymać usługę...")
            subprocess.run(['sc', 'stop', 'DBMonitorService'], check=False)
            time.sleep(3)  # Daj czas na zatrzymanie
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania usługi: {e}")

        # 2. Spróbuj usunąć usługę
        try:
            logger.info("Próbuję usunąć usługę...")
            subprocess.run(['sc', 'delete', 'DBMonitorService'], check=False)
            time.sleep(2)  # Daj czas na usunięcie
        except Exception as e:
            logger.error(f"Błąd podczas usuwania usługi: {e}")

        # 3. Zainstaluj usługę ponownie
        try:
            logger.info("Próbuję zainstalować usługę...")
            script_path = os.path.abspath(__file__)
            result = subprocess.run(
                [sys.executable, script_path, 'install'],
                check=True,
                capture_output=True,
                text=True,
                encoding='cp1250'
            )
            logger.info(f"Wynik instalacji: {result.stdout}")
            if result.stderr:
                logger.error(f"Błędy podczas instalacji: {result.stderr}")
        except Exception as e:
            logger.error(f"Błąd podczas instalacji usługi: {e}")
            return False

        # 4. Uruchom usługę
        try:
            logger.info("Próbuję uruchomić usługę...")
            subprocess.run(['sc', 'start', 'DBMonitorService'], check=True)
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania usługi: {e}")
            return False

        logger.info("Naprawa usługi zakończona powodzeniem")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas naprawy usługi: {e}")
        return False


if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            # Standardowe uruchomienie usługi
            logger.info("Standardowe uruchomienie usługi")
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(DBMonitorService)
            servicemanager.StartServiceCtrlDispatcher()
        elif sys.argv[1] == 'debug':
            # Tryb debugowania bezpośrednio w głównej metodzie main
            logger.info("Uruchamianie w trybie debug")
            service = DBMonitorService(['db_monitor.py', 'debug'])
            service.main()
        elif sys.argv[1] == 'status':
            show_logs()
        elif sys.argv[1] == 'test':
            # Bezpośredni test uruchomienia sql2html.py
            logger.info(
                "Uruchamianie testu bezpośredniego wywołania sql2html.py")
            success = run_direct()
            logger.info(
                f"Test zakończony {'sukcesem' if success else 'niepowodzeniem'}")
        elif sys.argv[1] == 'repair.py':
            # Tryb naprawy usługi
            logger.info("Uruchamianie trybu naprawy usługi")
            success = repair_service()
            logger.info(
                f"Naprawa zakończona {'sukcesem' if success else 'niepowodzeniem'}")
        else:
            # Standardowa obsługa komend Windows Service
            logger.info(f"Obsługa komendy Windows Service: {sys.argv[1]}")
            try:
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(DBMonitorService)
                win32serviceutil.HandleCommandLine(DBMonitorService)
            except Exception as e:
                logger.error(
                    f"Błąd podczas obsługi komendy Windows Service: {e}")
                logger.error(traceback.format_exc())
                raise
    except Exception as e:
        logger.error(f"Błąd krytyczny podczas uruchamiania usługi: {e}")
        logger.error(traceback.format_exc())
        raise
