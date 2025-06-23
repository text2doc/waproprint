import os
import time
import datetime
import win32print
import win32api
import pythoncom

import pyodbc
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Konfiguracja logowania
from lib.log_config import get_logger

logger = get_logger().getLogger(__name__)


class DocumentProcessor:
    """Przetwarzanie dokumentów (generowanie PDF i drukowanie)"""

    def __init__(self, db_manager, printer_name, temp_folder):
        self.db_manager = db_manager
        self.printer_name = printer_name
        self.temp_folder = temp_folder

    def process_document(self, document):
        """Przetwarza dokument - generuje PDF i drukuje"""
        try:
            logger.info(
                f"Przetwarzanie dokumentu {document['number']} (ID: {document['id']})")

            # Pobranie pozycji dokumentu
            items = self.db_manager.get_document_items(document['id'])

            if not items:
                logger.warning(
                    f"Dokument {document['number']} (ID: {document['id']}) nie zawiera żadnych pozycji")
                return False

            # Generowanie pliku PDF
            pdf_path = os.path.join(
                self.temp_folder, f"ZO_{document['id']}_{int(time.time())}.pdf")

            if self.generate_pdf(document, items, pdf_path):
                # Drukowanie dokumentu
                if self.print_pdf(pdf_path):
                    # Aktualizacja historii wydruku
                    if self.db_manager.update_print_history(document['id']):
                        logger.info(
                            f"Dokument {document['number']} (ID: {document['id']}) został pomyślnie przetworzony i wydrukowany")
                        return True

            return False

        except Exception as e:
            logger.error(
                f"Błąd podczas przetwarzania dokumentu {document['number']} (ID: {document['id']}): {e}")
            return False

    def generate_pdf(self, document, items, output_path):
        """Generuje plik PDF z dokumentem zamówienia"""
        try:
            # Upewnij się, że folder tymczasowy istnieje
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Inicjalizacja stylu
            styles = getSampleStyleSheet()
            styleN = styles['Normal']
            styleH = styles['Heading1']
            styleH2 = styles['Heading2']
            styleB = ParagraphStyle(
                'BodyText',
                parent=styles['Normal'],
                fontSize=9,
                leading=11
            )

            # Tworzymy dokument PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=10*mm,
                bottomMargin=10*mm
            )

            # Elementy dokumentu
            elements = []

            # Tytuł dokumentu
            elements.append(
                Paragraph(f"ZAMÓWIENIE ODBIORCY: {document['number']}", styleH))
            elements.append(Spacer(1, 5*mm))

            # Data wydruku
            elements.append(Paragraph(
                f"Data wydruku: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styleB))
            elements.append(Spacer(1, 5*mm))

            # Dane klienta
            customer_info = [
                ["DANE KLIENTA:"],
                [document['customer_name']],
                [document['customer_address']],
                [f"{document['customer_zipcode']} {document['customer_city']}"]
            ]

            customer_table = Table(customer_info, colWidths=[180*mm])
            customer_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
                ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
            ]))

            elements.append(customer_table)
            elements.append(Spacer(1, 5*mm))

            # Komentarz do dokumentu
            if document['comment']:
                comment_info = [
                    ["KOMENTARZ:"],
                    [document['comment']]
                ]

                comment_table = Table(comment_info, colWidths=[180*mm])
                comment_table.setStyle(TableStyle([
                    ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
                    ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 9),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
                ]))

                elements.append(comment_table)
                elements.append(Spacer(1, 5*mm))

            # Pozycje dokumentu
            elements.append(Paragraph("POZYCJE ZAMÓWIENIA:", styleH2))
            elements.append(Spacer(1, 3*mm))

            # Tabela z pozycjami
            data = [['LP', 'Kod', 'Nazwa', 'Ilość', 'J.m.']]

            for i, item in enumerate(items, 1):
                data.append([
                    str(i),
                    item['product_symbol'],
                    item['product_name'],
                    str(item['quantity']),
                    item['unit']
                ])

            # Utworzenie tabeli
            table = Table(data, colWidths=[10*mm, 30*mm, 100*mm, 20*mm, 20*mm])

            # Styl tabeli
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 8),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (4, -1), 'CENTER'),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 10*mm))

            # Podsumowanie
            elements.append(Paragraph(f"Liczba pozycji: {len(items)}", styleB))
            elements.append(Spacer(1, 1*mm))
            elements.append(
                Paragraph(f"Operator: {document['operator_id']}", styleB))
            elements.append(Spacer(1, 1*mm))
            elements.append(Paragraph(
                f"Wydrukowano: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styleB))

            # Zapisanie dokumentu
            doc.build(elements)

            logger.info(f"Wygenerowano plik PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas generowania PDF: {e}")
            return False

    def print_pdf(self, pdf_path):
        """Drukuje dokument PDF na wskazanej drukarce"""
        try:
            logger.info(
                f"Drukowanie dokumentu {pdf_path} na drukarce {self.printer_name}")

            # Inicjalizacja COM
            pythoncom.CoInitialize()

            # Sprawdzenie czy plik istnieje
            if not os.path.exists(pdf_path):
                logger.error(f"Plik PDF nie istnieje: {pdf_path}")
                return False

            # Drukowanie za pomocą domyślnej aplikacji dla plików PDF
            win32api.ShellExecute(
                0,
                "print",
                pdf_path,
                f'/d:"{self.printer_name}"',
                ".",
                0
            )

            # Dajemy czas na rozpoczęcie drukowania
            time.sleep(2)

            logger.info(f"Dokument został wysłany do drukarki")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas drukowania dokumentu: {e}")
            return False
