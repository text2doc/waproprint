#!/usr/bin/env python
# -*- coding: utf-8 -*-
# html2pdfs/pdf_trimmer.py

"""
Moduł do przycinania plików PDF na podstawie zawartości
Zapewnia funkcjonalność obcinania pustych przestrzeni, zachowując górę dokumentu
"""

import os
import shutil
import logging
from PyPDF2 import PdfReader, PdfWriter
from html2pdfs.utils import generate_temp_filename

# Importy opcjonalne
try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    import numpy as np

    PIL_NUMPY_AVAILABLE = True
except ImportError:
    PIL_NUMPY_AVAILABLE = False

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def trim_pdf_to_content(pdf_path, output_path=None):
    """
    Przycina istniejący PDF do rzeczywistej wysokości zawartości, zachowując górną część.

    Args:
        pdf_path (str): Ścieżka do pliku PDF do przycięcia
        output_path (str, optional): Ścieżka do zapisania przyciętego PDF. Jeśli None, nadpisuje oryginalny plik.

    Returns:
        str: Ścieżka do przyciętego pliku PDF
    """
    try:
        # Jeśli nie podano ścieżki wyjściowej, użyj tymczasowego pliku
        if output_path is None:
            temp_output = generate_temp_filename(prefix="trimmed_pdf")
            will_overwrite = True
        else:
            temp_output = output_path
            will_overwrite = False

        # Wykryj rzeczywistą wysokość zawartości
        content_height_mm = detect_content_height_from_pdf(pdf_path)
        logger.info(
            f"Wykryto wysokość zawartości PDF: {content_height_mm:.2f}mm")

        # Dodaj margines bezpieczeństwa (10%)
        # final_height_mm = content_height_mm * 1.1
        final_height_mm = content_height_mm * 1
        logger.info(
            f"Używam wysokości z marginesem bezpieczeństwa: {final_height_mm:.2f}mm")

        # Sprawdź, która biblioteka jest dostępna
        if PYMUPDF_AVAILABLE:
            # Użyj PyMuPDF do przycinania PDF
            doc = fitz.open(pdf_path)

            # Pobierz rozmiar strony
            page = doc[0]
            width_pts = page.rect.width
            original_height_pts = page.rect.height

            # Konwersja mm na punkty (1 mm = 2.83465 punktu)
            content_height_pts = final_height_mm * 2.83465

            # Sprawdź, czy potrzebne jest przycinanie
            if content_height_pts >= original_height_pts:
                logger.info(
                    "Wysokość treści jest większa lub równa wysokości dokumentu - przycinanie nie jest potrzebne")
                if will_overwrite:
                    return pdf_path
                else:
                    shutil.copy2(pdf_path, temp_output)
                    return temp_output

            # Utwórz nowy dokument z prawidłową wysokością
            new_doc = fitz.open()

            # Dla każdej strony w oryginalnym dokumencie
            for page_num in range(len(doc)):
                # Utwórz nową stronę o prawidłowej wysokości
                page = doc[page_num]
                new_page = new_doc.new_page(
                    width=width_pts, height=content_height_pts)

                # Skopiuj zawartość z oryginalnej strony, zachowując górną część
                rect = fitz.Rect(0, 0, width_pts, content_height_pts)
                new_page.show_pdf_page(rect, doc, page_num, clip=rect)

            # Zapisz zmodyfikowany PDF
            new_doc.save(temp_output)
            new_doc.close()
            doc.close()

            logger.info(
                f"Przycięto PDF używając PyMuPDF do wysokości {final_height_mm:.2f}mm")

        else:
            # Użyj PyPDF2 do prostszego przycięcia
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            # Dla każdej strony
            for i, page in enumerate(reader.pages):
                # Pobierz MediaBox
                media_box = page.mediabox
                original_width = float(media_box[2]) - float(media_box[0])
                original_height = float(media_box[3]) - float(media_box[1])

                # Konwersja mm na punkty (1 mm = 2.83465 punktu)
                content_height_pts = final_height_mm * 2.83465

                # Sprawdź, czy potrzebne jest przycinanie
                if content_height_pts >= original_height:
                    logger.info(
                        "Wysokość treści jest większa lub równa wysokości dokumentu - przycinanie nie jest potrzebne")
                    if will_overwrite:
                        return pdf_path
                    else:
                        shutil.copy2(pdf_path, temp_output)
                        return temp_output

                # Zmień rozmiar strony, zachowując górną część
                new_page = reader.pages[i]

                # Ustaw nowy MediaBox, zachowując górę strony
                # x0, y0 - lewy dolny róg
                # x1, y1 - prawy górny róg
                x0 = float(media_box[0])
                y0 = float(media_box[1])
                x1 = float(media_box[2])
                y1 = y0 + content_height_pts  # Górna granica przyciętego obszaru

                # Przytnij stronę do nowego rozmiaru
                new_page.mediabox.lower_left = (x0, y0)
                new_page.mediabox.upper_right = (x1, y1)

                # Dodaj stronę do nowego dokumentu
                writer.add_page(new_page)

            # Zapisz wynikowy PDF
            with open(temp_output, 'wb') as f:
                writer.write(f)

            logger.info(
                f"Przycięto PDF używając PyPDF2 do wysokości {final_height_mm:.2f}mm")

        # Jeśli mamy nadpisać oryginalny plik
        if will_overwrite:
            # Zrób kopię zapasową oryginalnego pliku
            backup_path = pdf_path + ".bak"
            shutil.copy2(pdf_path, backup_path)
            logger.debug(
                f"Utworzono kopię zapasową oryginalnego PDF: {backup_path}")

            # Nadpisz oryginalny plik
            shutil.move(temp_output, pdf_path)
            logger.info(f"Nadpisano oryginalny plik: {pdf_path}")
            os.remove(backup_path)

            return pdf_path
        else:
            logger.info(f"Zapisano przycięty PDF do: {temp_output}")
            return temp_output

    except Exception as e:
        logger.error(f"Błąd podczas przycinania PDF: {e}")
        if output_path is None and 'temp_output' in locals():
            # Jeśli mieliśmy nadpisać oryginalny plik, ale wystąpił błąd
            logger.warning(f"Zachowuję oryginalny plik bez zmian: {pdf_path}")
            return pdf_path
        else:
            # Jeśli podano ścieżkę wyjściową, ale wystąpił błąd, zwróć oryginalną ścieżkę
            logger.warning(
                f"Nie udało się utworzyć przyciętego PDF. Zwracam ścieżkę oryginału: {pdf_path}")
            return pdf_path


def detect_content_height_from_pdf(pdf_file):
    """
    Analizuje PDF i wykrywa rzeczywistą wysokość zawartości.

    Args:
        pdf_file (str): Ścieżka do pliku PDF

    Returns:
        float: Rzeczywista wysokość zawartości w mm
    """
    # Najpierw próbujemy z PyMuPDF (jeśli dostępny)
    if PYMUPDF_AVAILABLE:
        try:
            return detect_content_height_pymupdf(pdf_file)
        except Exception as e:
            logger.warning(f"Błąd podczas analizy PDF z PyMuPDF: {e}")

    # Następnie próbujemy z PIL + numpy (jeśli dostępne)
    if PIL_NUMPY_AVAILABLE:
        try:
            return detect_content_height_pil(pdf_file)
        except Exception as e:
            logger.warning(f"Błąd podczas analizy PDF z PIL: {e}")

    # Jeśli żadna z metod nie zadziała, używamy PyPDF2
    try:
        return detect_content_height_pypdf2(pdf_file)
    except Exception as e:
        logger.warning(f"Błąd podczas analizy PDF z PyPDF2: {e}")
        # Zwracamy wartość domyślną jeśli wszystkie metody zawiodą
        return 800.0  # Bezpieczna domyślna wartość


def detect_content_height_pymupdf(pdf_file):
    """
    Wykrywa rzeczywistą wysokość zawartości PDF używając PyMuPDF.

    Args:
        pdf_file (str): Ścieżka do pliku PDF

    Returns:
        float: Rzeczywista wysokość zawartości w mm
    """
    doc = fitz.open(pdf_file)
    max_y = 0

    # Analizuj wszystkie strony PDF
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Pobierz zawartość strony jako bloki tekstu
        blocks = page.get_text("blocks")

        # Znajdź największą współrzędną Y (najniższy punkt tekstu)
        for block in blocks:
            # Współrzędne bloku (x0, y0, x1, y1, ...)
            _, _, _, block_y1, *_ = block[:4]
            max_y = max(max_y, block_y1)

        # Sprawdź również elementy graficzne
        for img in page.get_images(full=True):
            xref = img[0]
            bbox = page.get_image_bbox(xref)
            if bbox:
                max_y = max(max_y, bbox.y1)

    # Konwersja z punktów na mm (1 punkt = 0.3528 mm)
    max_y_mm = max_y * 0.3528

    # Dodaj mały margines bezpieczeństwa
    max_y_mm = max_y_mm + 10.0

    logger.info(f"Wykryto wysokość zawartości (PyMuPDF): {max_y_mm:.2f}mm")
    return max_y_mm


def detect_content_height_pil(pdf_file):
    """
    Wykrywa rzeczywistą wysokość zawartości PDF używając PIL i numpy.

    Args:
        pdf_file (str): Ścieżka do pliku PDF

    Returns:
        float: Rzeczywista wysokość zawartości w mm
    """
    # Konwertuj PDF na obrazy (tylko pierwszą stronę)
    pdf_images = convert_pdf_to_images(pdf_file)

    if not pdf_images or len(pdf_images) == 0:
        raise ValueError("Nie udało się przekonwertować PDF na obrazy")

    max_y = 0
    dpi = 72.0  # Domyślny DPI dla PDF

    # Analizuj każdy obraz strony
    for img in pdf_images:
        # Konwertuj na czarno-biały i do tablicy numpy
        img_bw = img.convert('L')
        img_array = np.array(img_bw)

        # Znajdź wiersze zawierające treść (niepuste piksele)
        # Niższy próg (np. 240 zamiast 250) aby wykryć jaśniejszy tekst
        non_empty_rows = np.where(np.min(img_array, axis=1) < 240)[0]

        if len(non_empty_rows) > 0:
            last_row = non_empty_rows[-1]
            max_y = max(max_y, last_row)

    # Konwersja z pikseli na mm (przy DPI 72)
    max_y_mm = (max_y / dpi) * 25.4

    # Dodaj margines bezpieczeństwa
    max_y_mm = max_y_mm + 15.0  # Zwiększony margines dla bezpieczeństwa

    logger.info(f"Wykryto wysokość zawartości (PIL): {max_y_mm:.2f}mm")
    return max_y_mm


# Zwiększone DPI dla lepszej dokładności
def convert_pdf_to_images(pdf_file, dpi=150):
    """
    Konwertuje strony PDF na obrazy.

    Args:
        pdf_file (str): Ścieżka do pliku PDF
        dpi (int): Rozdzielczość konwersji

    Returns:
        list: Lista obiektów PIL.Image
    """
    try:
        # Próbujemy użyć biblioteki pdf2image jeśli dostępna
        import pdf2image
        return pdf2image.convert_from_path(pdf_file, dpi=dpi)
    except ImportError:
        # Alternatywnie używamy PyMuPDF jeśli dostępny
        if PYMUPDF_AVAILABLE:
            doc = fitz.open(pdf_file)
            images = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Używamy wyższej rozdzielczości dla lepszej dokładności
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples)
                images.append(img)

            return images
        else:
            logger.warning(
                "Brak wymaganych bibliotek do konwersji PDF na obrazy")
            return []


def detect_content_height_pypdf2(pdf_file):
    """
    Wykrywa przybliżoną wysokość zawartości PDF używając PyPDF2.

    Args:
        pdf_file (str): Ścieżka do pliku PDF

    Returns:
        float: Przybliżona wysokość zawartości w mm
    """
    reader = PdfReader(pdf_file)
    max_y = 0

    # Analizuj wszystkie strony PDF
    for page in reader.pages:
        # Pobierz MediaBox, która definiuje rozmiar strony
        media_box = page.mediabox

        # MediaBox to lista [x0, y0, x1, y1]
        # Wysokość strony to y1 - y0
        height_pts = float(media_box[3]) - float(media_box[1])

        # Zakładamy, że zawartość zajmuje 95% wysokości strony
        # Jest to przybliżenie, ponieważ PyPDF2 nie daje bezpośredniego dostępu do zawartości
        # Używamy większej wartości (97% zamiast 95%)
        height_pts = height_pts * 0.97

        max_y = max(max_y, height_pts)

    # Konwersja z punktów na mm (1 punkt = 0.3528 mm)
    max_y_mm = max_y * 0.3528

    logger.info(f"Wykryto wysokość zawartości (PyPDF2): {max_y_mm:.2f}mm")
    return max_y_mm


def trim_existing_pdf(pdf_path, page_width_inches=None, margin_mm=None, dpi=None):
    """
    Obcina istniejący plik PDF do optymalnej wysokości i zastępuje go w tej samej ścieżce.
    Parametry są opcjonalne, jeśli nie są podane, są wykrywane z PDF.

    Args:
        pdf_path (str): Ścieżka do pliku PDF, który ma zostać obcięty
        page_width_inches (float, optional): Szerokość strony w calach
        margin_mm (int, optional): Margines w milimetrach
        dpi (int, optional): Rozdzielczość w DPI

    Returns:
        str: Ścieżka do obciętego pliku PDF (ta sama co wejściowa)
    """
    try:
        logger.info(f"Obcinanie istniejącego PDF: {pdf_path}")

        # Sprawdź, czy plik istnieje
        if not os.path.exists(pdf_path):
            logger.error(f"Plik PDF nie istnieje: {pdf_path}")
            return None

        # Utwórz kopię zapasową oryginalnego pliku PDF
        backup_path = pdf_path + ".original"
        shutil.copy2(pdf_path, backup_path)
        logger.info(
            f"Utworzono kopię zapasową oryginalnego PDF: {backup_path}")

        # Przycięcie PDF do zawartości
        result = trim_pdf_to_content(pdf_path)

        if result:
            logger.info(f"Pomyślnie przycięto PDF: {result}")
            # usun ten plik
            os.remove(backup_path)
            return result
        else:
            logger.error("Nie udało się przyciąć PDF")
            # Przywróć oryginalny plik z kopii zapasowej
            shutil.copy2(backup_path, pdf_path)
            logger.info("Przywrócono oryginalny PDF z kopii zapasowej")
            return None

    except Exception as e:
        logger.error(f"Błąd podczas obcinania istniejącego PDF: {e}")
        # Próba przywrócenia oryginału z kopii zapasowej
        backup_path = pdf_path + ".original"
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, pdf_path)
            logger.info(
                "Przywrócono oryginalny PDF z kopii zapasowej po błędzie")
        return None
