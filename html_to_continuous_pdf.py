#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# html_to_continuous_pdf.py

"""
Skrypt do konwersji HTML do ciągłego PDF (bez podziału na strony) z naprawioną obsługą plików.
Rozwiązuje problemy z prawami dostępu i zajętymi plikami, jednocześnie generując PDF
w formacie ciągłym, odpowiednim dla drukarek termicznych.
"""

import os
import sys
import argparse
import logging
import tempfile
import shutil

# Importuj moduły pomocnicze
from pdf_utils import (
    find_wkhtmltopdf_path, generate_temp_filename, ensure_directory_exists,
    preprocess_html, calculate_optimal_height, run_wkhtmltopdf, pdf_to_final_location
)
from pdf_analysis import get_optimal_pdf_height

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def html_to_continuous_pdf(html_file, pdf_file=None, page_width=4.0, margin=5, dpi=203, two_pass=True):
    """
    Konwertuje plik HTML do ciągłego PDF używając wkhtmltopdf

    Args:
        html_file (str): Ścieżka do pliku HTML
        pdf_file (str, optional): Ścieżka do pliku wyjściowego PDF
        page_width (float): Szerokość strony w calach
        margin (int): Margines w milimetrach
        dpi (int): Rozdzielczość w DPI
        two_pass (bool): Czy używać podejścia dwuprzebiegowego

    Returns:
        str: Ścieżka do wygenerowanego pliku PDF
    """
    if pdf_file is None:
        # Generuj nazwę w katalogu tymczasowym
        pdf_file = generate_temp_filename()

    # Przetwórz HTML, aby zapobiec podziałowi na strony
    processed_html = preprocess_html(html_file)

    try:
        # Znajdź wkhtmltopdf
        wkhtmltopdf_path = find_wkhtmltopdf_path()

        if not wkhtmltopdf_path:
            logger.error("Nie znaleziono wkhtmltopdf.")
            raise FileNotFoundError("Nie znaleziono wkhtmltopdf")

        logger.info(f"Używam wkhtmltopdf z: {wkhtmltopdf_path}")

        # Konwersja szerokości z cali na mm
        page_width_mm = page_width * 25.4  # cale na mm

        # Sprawdź czy dostępne są moduły do analizy PDF
        from pdf_analysis import PYMUPDF_AVAILABLE, PIL_NUMPY_AVAILABLE

        if two_pass and (PYMUPDF_AVAILABLE and PIL_NUMPY_AVAILABLE):
            # PIERWSZY PRZEBIEG - wygeneruj PDF z dużą wysokością
            logger.info("Pierwszy przebieg - generowanie wstępnego PDF do analizy...")

            # Użyj bardzo dużej wysokości dla pierwszego przebiegu
            first_pass_options = [
                '--page-width', f'{page_width_mm}mm',
                '--page-height', '5000mm',  # Duża wysokość do pierwszego przebiegu
                '--margin-top', f'{margin}mm',
                '--margin-bottom', f'{margin}mm',
                '--margin-left', f'{margin}mm',
                '--margin-right', f'{margin}mm',
                '--dpi', str(dpi),
                '--enable-local-file-access',
                '--print-media-type',
                '--disable-smart-shrinking',
                '--no-background',
                '--zoom', '1.0'
            ]

            temp_pdf = generate_temp_filename(prefix="first_pass")
            success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, temp_pdf, first_pass_options)

            if not success:
                logger.warning("Pierwszy przebieg nie powiódł się, próbuję z prostszymi opcjami...")
                first_pass_options = [
                    '--page-width', f'{page_width_mm}mm',
                    '--disable-smart-shrinking'
                ]
                success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, temp_pdf, first_pass_options)

            if success:
                # Analizuj wygenerowany PDF, aby wykryć rzeczywistą wysokość zawartości
                try:
                    # Użyj funkcji która dzieli PDF i znajduje dokładny koniec treści
                    optimal_height_mm = get_optimal_pdf_height(temp_pdf)

                    if optimal_height_mm is not None:
                        logger.info(f"Wykryta rzeczywista wysokość treści: {optimal_height_mm:.2f}mm")

                        # DRUGI PRZEBIEG - wygeneruj PDF z dokładnie określoną wysokością
                        logger.info("Drugi przebieg - generowanie ostatecznego PDF z dokładną wysokością...")

                        second_pass_options = [
                            '--page-width', f'{page_width_mm}mm',
                            '--page-height', f'{optimal_height_mm}mm',
                            '--margin-top', f'{margin}mm',
                            '--margin-bottom', f'{margin}mm',
                            '--margin-left', f'{margin}mm',
                            '--margin-right', f'{margin}mm',
                            '--dpi', str(dpi),
                            '--enable-local-file-access',
                            '--print-media-type',
                            '--disable-smart-shrinking',
                            '--no-background',
                            '--zoom', '1.0',
                            # '--disable-pdf-compression',
                            '--no-outline'
                        ]

                        success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, pdf_file, second_pass_options)

                        # Usuń tymczasowy plik z pierwszego przebiegu
                        try:
                            os.unlink(temp_pdf)
                        except:
                            pass

                        if success:
                            logger.info("Drugi przebieg zakończony sukcesem.")
                            return pdf_file

                except Exception as e:
                    logger.warning(f"Błąd podczas analizy PDF: {e}")
                    # Kontynuuj z domyślnym podejściem jeśli analiza zawiedzie
                    logger.info("Używam domyślnego podejścia...")

            # Jeśli drugi przebieg się nie powiódł lub wystąpił błąd, kontynuuj z domyślnym podejściem

        # Standardowe podejście - użyj szacowanej wysokości na podstawie treści HTML
        estimated_height_mm = calculate_optimal_height(html_file)
        logger.info(f"Używam szacowanej wysokości: {estimated_height_mm:.2f}mm")

        continuous_options = [
            '--page-width', f'{page_width_mm}mm',
            '--page-height', f'{estimated_height_mm + 20}mm',  # Dodaj dodatkowe 20mm
            '--margin-top', f'{margin}mm',
            '--margin-bottom', f'{margin}mm',
            '--margin-left', f'{margin}mm',
            '--margin-right', f'{margin}mm',
            '--dpi', str(dpi),
            '--enable-local-file-access',
            '--print-media-type',
            '--disable-smart-shrinking',
            '--no-background',
            '--zoom', '1.0',
            # '--disable-pdf-compression',
            # '--no-pdf-compression',
            '--no-outline',
            '--javascript-delay', '1000'
        ]

        # Najpierw spróbuj z opcjami dla ciągłego wydruku
        success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, pdf_file, continuous_options)

        if not success:
            logger.info("Pierwszy sposób nie zadziałał, próbuję z prostszymi opcjami...")

            # Jeśli nie zadziałało, spróbuj z minimalnymi opcjami
            minimal_options = [
                '--page-width', f'{page_width_mm}mm',
                '--margin-top', f'{margin}mm',
                '--margin-bottom', f'{margin}mm',
                '--margin-left', f'{margin}mm',
                '--margin-right', f'{margin}mm',
                '--dpi', str(dpi),
                '--quiet',
                '--disable-smart-shrinking'
            ]

            success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, pdf_file, minimal_options)

            if not success:
                logger.info("Próbuję z absolutnie minimalnymi opcjami...")

                # Jeśli nadal nie zadziałało, spróbuj z absolutnie minimalnymi opcjami
                success = run_wkhtmltopdf(wkhtmltopdf_path, processed_html, pdf_file, [])

                if not success:
                    logger.error("Wszystkie metody konwersji nie powiodły się")
                    raise RuntimeError("Nie udało się wygenerować pliku PDF")

        # Sprawdź, czy PDF został wygenerowany i ma rozmiar większy od zera
        if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
            logger.info(f"PDF wygenerowany pomyślnie: {pdf_file}")
            logger.info(f"Rozmiar pliku PDF: {os.path.getsize(pdf_file) / 1024:.2f} KB")
            return pdf_file
        else:
            logger.error("PDF nie został wygenerowany lub ma zerowy rozmiar")
            raise RuntimeError("Nie udało się wygenerować pliku PDF")

    except Exception as e:
        logger.error(f"Błąd podczas konwersji HTML do PDF: {e}")
        raise

    finally:
        # Usuń tymczasowy plik HTML
        try:
            if os.path.exists(processed_html):
                os.unlink(processed_html)
                logger.debug(f"Usunięto tymczasowy plik HTML: {processed_html}")
        except:
            pass


def parse_arguments():
    """
    Parsuje argumenty linii poleceń

    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(
        description='Konwersja HTML do ciągłego PDF z poprawioną obsługą plików'
    )
    parser.add_argument('input_file', help='Ścieżka do pliku HTML')
    parser.add_argument('-o', '--output', help='Ścieżka do pliku wyjściowego PDF')
    parser.add_argument('--width', type=float, default=4.0, help='Szerokość strony w calach (domyślnie 4.0)')
    parser.add_argument('--margin', type=int, default=5, help='Margines w milimetrach (domyślnie 5)')
    parser.add_argument('--dpi', type=int, default=203, help='Rozdzielczość w DPI (domyślnie 203)')
    parser.add_argument('--items', type=int, help='Liczba pozycji w dokumencie (opcjonalnie)')
    parser.add_argument('--single-pass', action='store_true', help='Używaj tylko jednego przebiegu konwersji')
    parser.add_argument('--split-pdf', action='store_true', help='Podziel PDF na treść i białą przestrzeń')
    parser.add_argument('--verbose', '-v', action='store_true', help='Wyświetlaj szczegółowe komunikaty')

    return parser.parse_args()


def convert_html_to_pdf(args):
    """
    Główna funkcja konwersji HTML do PDF z obsługą argumentów

    Args:
        args (argparse.Namespace): Sparsowane argumenty linii poleceń

    Returns:
        int: Kod zakończenia (0 - sukces, 1 - błąd)
    """
    # Ustaw poziom logowania
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Sprawdź czy plik wejściowy istnieje
        if not os.path.isfile(args.input_file):
            logger.error(f"Plik wejściowy nie istnieje: {args.input_file}")
            return 1

        # Jeśli podano liczbę pozycji, wyświetl informację
        if args.items:
            logger.info(f"Używam podanej liczby pozycji: {args.items}")
            # Obliczmy i wyświetlmy optymalną wysokość
            optimal_height = calculate_optimal_height(args.input_file, args.items)
            logger.info(f"Optymalna wysokość dokumentu: {optimal_height}mm")

        # Konwersja HTML do PDF
        # temp_pdf = html_to_continuous_pdf(
        #     args.input_file,
        #     None,  # Najpierw generuj do pliku tymczasowego
        #     args.width,
        #     args.margin,
        #     args.dpi,
        #     not args.single_pass  # Używaj dwuprzebiegowego podejścia, chyba że podano --single-pass
        # )

        temp_pdf = html_to_continuous_pdf(
            html_file=args.input_file,

            pdf_file=None,
            page_width=args.width,
            margin=args.margin,  # Zmniejsz margines
            dpi=args.dpi,
            two_pass=args.single_pass
        )

        # Jeśli wybrano opcję podziału PDF
        if args.split_pdf and temp_pdf:
            try:
                from pdf_analysis import split_pdf_at_content_end, PYMUPDF_AVAILABLE, PIL_NUMPY_AVAILABLE

                if PYMUPDF_AVAILABLE and PIL_NUMPY_AVAILABLE:
                    # Podziel PDF na część z treścią i białą przestrzeń
                    content_pdf = os.path.splitext(temp_pdf)[0] + "_content.pdf"
                    blank_pdf = os.path.splitext(temp_pdf)[0] + "_blank.pdf"

                    logger.info("Dzielenie PDF na treść i białą przestrzeń...")
                    content_height, content_path, blank_path = split_pdf_at_content_end(
                        temp_pdf, content_pdf, blank_pdf
                    )

                    if content_height and content_path:
                        logger.info(f"Podzielono PDF. Wysokość treści: {content_height:.2f}mm")
                        logger.info(f"Treść zapisana do: {content_path}")
                        logger.info(f"Biała przestrzeń zapisana do: {blank_path}")

                        # Użyj treści jako finalnego PDF
                        temp_pdf = content_path
                else:
                    logger.warning("Nie można podzielić PDF - brak wymaganych bibliotek (PyMuPDF, PIL, NumPy)")
            except Exception as e:
                logger.error(f"Błąd podczas dzielenia PDF: {e}")

        # Jeśli podano ścieżkę wyjściową, skopiuj tam plik
        if args.output:
            final_pdf = pdf_to_final_location(temp_pdf, args.output)
            if final_pdf != args.output:
                logger.warning(
                    f"Nie udało się zapisać pliku w żądanej lokalizacji. Plik został zapisany jako: {final_pdf}")
        else:
            # Jeśli nie podano ścieżki wyjściowej, użyj domyślnej nazwy w tym samym katalogu co wejściowy
            default_output = os.path.splitext(args.input_file)[0] + '.pdf'
            final_pdf = pdf_to_final_location(temp_pdf, default_output)

        logger.info(f"Konwersja zakończona pomyślnie. Wygenerowano plik: {final_pdf}")
        return 0

    except Exception as e:
        logger.error(f"Wystąpił błąd: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """Główna funkcja skryptu wywołująca parsowanie argumentów i konwersję"""
    # Parsuj argumenty
    # args = parse_arguments()

    temp_pdf = html_to_continuous_pdf(
        html_file='zamowienie.html',
        pdf_file='zamowienie.pdf',
        # pdf_file=None,
        page_width=4.0,
        margin=5,
        dpi=203,
        two_pass=True
    )


    try:
        from pdf_analysis import split_pdf_at_content_end, PYMUPDF_AVAILABLE, PIL_NUMPY_AVAILABLE

        if PYMUPDF_AVAILABLE and PIL_NUMPY_AVAILABLE:
            # Podziel PDF na część z treścią i białą przestrzeń
            content_pdf = os.path.splitext(temp_pdf)[0] + "_content.pdf"
            blank_pdf = os.path.splitext(temp_pdf)[0] + "_blank.pdf"

            logger.info("Dzielenie PDF na treść i białą przestrzeń...")
            content_height, content_path, blank_path = split_pdf_at_content_end(
                temp_pdf, content_pdf, blank_pdf
            )

            if content_height and content_path:
                logger.info(f"Podzielono PDF. Wysokość treści: {content_height:.2f}mm")
                logger.info(f"Treść zapisana do: {content_path}")
                logger.info(f"Biała przestrzeń zapisana do: {blank_path}")

                # Użyj treści jako finalnego PDF
                temp_pdf = content_path
        else:
            logger.warning("Nie można podzielić PDF - brak wymaganych bibliotek (PyMuPDF, PIL, NumPy)")
    except Exception as e:
        logger.error(f"Błąd podczas dzielenia PDF: {e}")

    # Wywołaj konwersję i zwróć kod zakończenia
    # return convert_html_to_pdf(args)


if __name__ == "__main__":
    main()
    # sys.exit(main())

#