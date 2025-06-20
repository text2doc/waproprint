#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler


class SingletonLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonLogger, cls).__new__(cls)
            cls._instance.initialize_logger()
        return cls._instance

    def initialize_logger(self):
        """Inicjalizuje logger"""
        # Tworzenie katalogów dla logów
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Konfiguracja głównego loggera
        logger = logging.getLogger('sql_runner')
        logger.setLevel(logging.DEBUG)

        # Zapobiegaj duplikacji handlera
        if logger.handlers:
            return

        # Konfiguracja formatera
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Handler pliku
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'sql_runner.log'),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Handler konsoli
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Dodanie handlerów do loggera
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        self.logger = logger

    def getLogger(self, name=None):
        """Zwraca logger z podaną nazwą"""
        if name:
            return logging.getLogger(name)
        return self.logger


def get_logger():
    """Funkcja pomocnicza zwracająca instancję SingletonLogger"""
    return SingletonLogger()