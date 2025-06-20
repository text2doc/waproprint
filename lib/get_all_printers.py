import os
import configparser
import win32print
import win32api
import logging
import platform
import socket
import subprocess
import re
import logging

def get_all_printers():
    """Pobiera listę wszystkich drukarek zainstalowanych w systemie"""
    try:
        printers = []
        for flags, description, name, comment in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
            printers.append({
                'name': name,
                'description': description,
                'comment': comment
            })
            logging.info(f"Znaleziono drukarkę: {name}")

        return printers
    except Exception as e:
        logging.error(f"Błąd podczas pobierania listy drukarek: {str(e)}")
        return []

def get_all_printers2():
    """Pobiera listę wszystkich dostępnych drukarek"""
    try:
        printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        logging.info("=== Lista dostępnych drukarek ===")
        for i, printer in enumerate(printers, 1):
            logging.info(f"{i}. {printer}")
        return printers
    except Exception as e:
        logging.error(f"Błąd podczas pobierania listy drukarek: {str(e)}")
        return []