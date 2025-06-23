#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  html_to_pdf_cont.py

"""
Główny moduł do konwersji HTML do ciągłego PDF
Integruje funkcjonalności z innych modułów do kompletnego procesu konwersji
"""

import shutil
import os
import sys
import logging
import subprocess
import argparse

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html2pdfs.utils import (
    find_wkhtmltopdf_path,
    generate_temp_filename,
    ensure_directory_exists,
    pdf_to_final_location
)
from html2pdfs.html_processor import preprocess_html, calculate_optimal_height
from html2pdfs.pdf_trimmer import (
    trim_pdf_to_content,
    detect_content_height_from_pdf,
    trim_existing_pdf
)

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def run_wkhtmltopdf(wkhtmltopdf_path, html_file, pdf_file, options):
    """
    Uruchamia wkhtmltopdf z podanymi opcjami.

    Args:
        wkhtmltopdf_path (str): Ścieżka do wkhtmltopdf
        html_file (str): Ścieżka do pliku HTML
        pdf_file (str): Ścieżka do pliku wyjściowego PDF
        options (list): Lista opcji dla wkhtmltopdf

    Returns:
        bool: True jeśli konwersja powiodła się, False w przeciwnym przypadku
    """
    try:
        # Upewnij się, że plik wyjściowy ma unikalną nazwę
        temp_pdf = pdf_file

        # Debugowanie - zapisz kopię zmodyfikowanego HTML
        debug_html = os.path.splitext(html_file)[0] + "_debug.html"
        try:
            import shutil
            shutil.copy2(html_file, debug_html)
            logger.debug(f"Zapisano kopię debug HTML: {debug_html}")
        except:
            pass

        # Uruchom komendę z dodatkowymi opcjami dla drukarki termicznej
        base_options = options.copy()

        # Dodaj dodatkowe opcje dla drukarki termicznej
        if '--page-height' not in ' '.join(base_options):
            base_options.extend(['--page-height', '30000mm'])

        if '--disable-smart-shrinking' not in ' '.join(base_options):
            base_options.append('--disable-smart-shrinking')

        # Zastosuj wszystkie możliwe opcje aby wymusić format ciągły
        base_options.extend(['--stop-slow-scripts', '--no-stop-slow-scripts'])

        cmd = [wkhtmltopdf_path] + base_options + [html_file, temp_pdf]

        logger.debug(f"Uruchamiam komendę: {' '.join(cmd)}")

        # Uruchom z większym limitem czasu dla dużych dokumentów
        if sys.platform.startswith('win'):
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        try:
            stdout, stderr = process.communicate(timeout=60)  # Większy timeout
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.warning("Przekroczono czas oczekiwania na wkhtmltopdf")

        if process.returncode != 0:
            logger.warning(
                f"wkhtmltopdf zakończył się kodem błędu {process.returncode}")
            if stderr:
                logger.warning(
                    f"Błąd: {stderr.decode('utf-8', errors='ignore')}")
            return False

        # Sprawdź, czy PDF został wygenerowany
        if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
            logger.info(
                f"PDF został wygenerowany pomyślnie, rozmiar: {os.path.getsize(temp_pdf) / 1024:.2f} KB")
            return True
        else:
            logger.warning(
                "Plik PDF nie został wygenerowany lub ma zerowy rozmiar")
            return False

    except Exception as e:
        logger.warning(f"Błąd podczas uruchamiania wkhtmltopdf: {e}")
        return False


def remove_white_space(input_pdf, output_pdf):
    """
    Usuwa zbędną białą przestrzeń z pliku PDF i konwertuje na format ciągły.

    Args:
        input_pdf (str): Ścieżka do źródłowego pliku PDF
        output_pdf (str): Ścieżka do docelowego pliku PDF

    Returns:
        bool: True jeśli operacja zakończyła się sukcesem, False w przeciwnym razie
    """
    try:
        # To jest teraz prosta operacja przycinania
        trimmed_pdf = trim_pdf_to_content(input_pdf, output_pdf)
        if trimmed_pdf:
            logger.info(
                f"Usunięto białą przestrzeń z PDF, zapisano do: {output_pdf}")
            return True
        else:
            logger.warning("Nie udało się usunąć białej przestrzeni")
            import shutil
            shutil.copy2(input_pdf, output_pdf)
            return False
    except Exception as e:
        logger.error(f"Błąd podczas usuwania białej przestrzeni: {e}")
        # Jeśli operacja się nie powiedzie, skopiuj oryginalny plik
        import shutil
        shutil.copy2(input_pdf, output_pdf)
        return False


def html_to_pdf_continuous(html_file, pdf_file=None, page_width=4.0, margin=5, dpi=203, two_pass=True):
    """
    Konwertuje plik HTML do ciągłego PDF używając wkhtmltopdf.

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

        if two_pass:
            # PIERWSZY PRZEBIEG - wygeneruj PDF z dużą wysokością
            logger.info(
                "Pierwszy przebieg - generowanie wstępnego PDF do analizy...")

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
            success = run_wkhtmltopdf(
                wkhtmltopdf_path, processed_html, temp_pdf, first_pass_options)

            if not success:
                logger.warning(
                    "Pierwszy przebieg nie powiódł się, próbuję z prostszymi opcjami...")
                first_pass_options = [
                    '--page-width', f'{page_width_mm}mm',
                    '--disable-smart-shrinking'
                ]
                success = run_wkhtmltopdf(
                    wkhtmltopdf_path, processed_html, temp_pdf, first_pass_options)

            if success:
                # Analizuj wygenerowany PDF, aby wykryć rzeczywistą wysokość zawartości
                try:
                    detected_height_mm = detect_content_height_from_pdf(
                        temp_pdf)
                    logger.info(
                        f"Wykryta rzeczywista wysokość zawartości: {detected_height_mm:.2f}mm")

                    # DRUGI PRZEBIEG - wygeneruj PDF z dokładnie określoną wysokością
                    logger.info(
                        "Drugi przebieg - generowanie ostatecznego PDF z dokładną wysokością...")

                    # Dodaj margines bezpieczeństwa do wykrytej wysokości (10%)
                    optimal_height_mm = detected_height_mm * 1.1
                    logger.info(
                        f"Używam wysokości z marginesem bezpieczeństwa: {optimal_height_mm:.2f}mm")

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
                        '--disable-pdf-compression',
                        '--no-outline'
                    ]

                    success = run_wkhtmltopdf(
                        wkhtmltopdf_path, processed_html, pdf_file, second_pass_options)

                    # Usuń tymczasowy plik z pierwszego przebiegu
                    try:
                        os.unlink(temp_pdf)
                    except:
                        pass

                    if success:
                        logger.info("Drugi przebieg zakończony sukcesem.")
                        # Przycięcie PDF do dokładnej wysokości zawartości
                        trimmed_pdf = trim_pdf_to_content(pdf_file)
                        return trimmed_pdf if trimmed_pdf else pdf_file

                except Exception as e:
                    logger.warning(f"Błąd podczas analizy PDF: {e}")
                    # Kontynuuj z domyślnym podejściem jeśli analiza zawiedzie
                    logger.info("Używam domyślnego podejścia...")

            # Jeśli drugi przebieg się nie powiódł lub wystąpił błąd, kontynuuj z domyślnym podejściem

        # Standardowe podejście - użyj szacowanej wysokości na podstawie treści HTML
        estimated_height_mm = calculate_optimal_height(html_file)
        logger.info(
            f"Używam szacowanej wysokości: {estimated_height_mm:.2f}mm")

        continuous_options = [
            '--page-width', f'{page_width_mm}mm',
            '--page-height', f'{estimated_height_mm}mm',
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
            '--disable-pdf-compression',
            '--no-pdf-compression',
            '--no-outline',
            '--javascript-delay', '1000'
        ]

        # Najpierw spróbuj z opcjami dla ciągłego wydruku
        temp_pdf = generate_temp_filename()
        success = run_wkhtmltopdf(
            wkhtmltopdf_path, processed_html, temp_pdf, continuous_options)

        if not success:
            logger.info(
                "Pierwszy sposób nie zadziałał, próbuję z prostszymi opcjami...")

            # Jeśli nie zadziałało, spróbuj z minimalnymi opcjami
            minimal_options = [
                '--quiet',
                '--disable-smart-shrinking',
                '--page-width', f'{page_width_mm}mm',
                '--margin-top', f'{margin}mm',
                '--margin-bottom', f'{margin}mm',
                '--margin-left', f'{margin}mm',
                '--margin-right', f'{margin}mm',
            ]

            success = run_wkhtmltopdf(
                wkhtmltopdf_path, processed_html, temp_pdf, minimal_options)

            if not success:
                logger.info("Próbuję z absolutnie minimalnymi opcjami...")

                # Jeśli nadal nie zadziałało, spróbuj z absolutnie minimalnymi opcjami
                success = run_wkhtmltopdf(
                    wkhtmltopdf_path, processed_html, temp_pdf, [])

                if not success:
                    logger.error("Wszystkie metody konwersji nie powiodły się")
                    raise RuntimeError("Nie udało się wygenerować pliku PDF")

        # Sprawdź, czy PDF został wygenerowany i ma rozmiar większy od zera
        if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
            logger.info(f"PDF wygenerowany pomyślnie: {temp_pdf}")
            logger.info(
                f"Rozmiar pliku PDF: {os.path.getsize(temp_pdf) / 1024:.2f} KB")

            # Usuń białą przestrzeń z PDF
            remove_white_space(temp_pdf, pdf_file)
            logger.info(f"Usunięto białą przestrzeń, zapisano do: {pdf_file}")

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
                logger.debug(
                    f"Usunięto tymczasowy plik HTML: {processed_html}")
        except:
            pass


def split_pdf_at_content_end(pdf_path, content_output_path=None, blank_output_path=None):
    """
    Dzieli PDF na część zawierającą treść i białą przestrzeń.

    Args:
        pdf_path (str): Ścieżka do pliku PDF
        content_output_path (str, optional): Ścieżka do zapisania części z treścią
        blank_output_path (str, optional): Ścieżka do zapisania części z białą przestrzenią

    Returns:
        tuple: (wysokość_treści_mm, ścieżka_do_treści, ścieżka_do_białej_przestrzeni)
    """
    try:
        # Ustaw domyślne ścieżki wyjściowe, jeśli nie podano
        if content_output_path is None:
            content_output_path = os.path.splitext(
                pdf_path)[0] + "_content.pdf"

        if blank_output_path is None:
            blank_output_path = os.path.splitext(pdf_path)[0] + "_blank.pdf"

        # Przycinanie do zawartości teraz wykonuje całą pracę
        trimmed_pdf = trim_pdf_to_content(pdf_path, content_output_path)

        # Funkcja ta teraz tylko opakowuje trim_pdf_to_content
        # Możemy usunąć tę funkcję w przyszłości, ale na razie zostawiamy dla kompatybilności
        if trimmed_pdf:
            content_height_mm = detect_content_height_from_pdf(trimmed_pdf)
            return content_height_mm, trimmed_pdf, blank_output_path

        return None, None, None

    except Exception as e:
        logger.error(f"Błąd podczas dzielenia PDF: {e}")
        return None, None, None


def parse_arguments():
    """
    Parsuje argumenty linii poleceń.

    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(
        description='Konwersja HTML do ciągłego PDF z poprawioną obsługą plików'
    )
    parser.add_argument('input_file', help='Ścieżka do pliku HTML lub PDF')
    parser.add_argument(
        '-o', '--output', help='Ścieżka do pliku wyjściowego PDF')
    parser.add_argument('--width', type=float, default=4.0,
                        help='Szerokość strony w calach (domyślnie 4.0)')
    parser.add_argument('--margin', type=int, default=5,
                        help='Margines w milimetrach (domyślnie 5)')
    parser.add_argument('--dpi', type=int, default=203,
                        help='Rozdzielczość w DPI (domyślnie 203)')
    parser.add_argument('--items', type=int,
                        help='Liczba pozycji w dokumencie (opcjonalnie)')
    parser.add_argument('--single-pass', action='store_true',
                        help='Używaj tylko jednego przebiegu konwersji')
    parser.add_argument('--split-pdf', action='store_true',
                        help='Podziel PDF na treść i białą przestrzeń')
    parser.add_argument('--trim-only', action='store_true',
                        help='Tylko przytnij istniejący PDF bez konwersji HTML')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Wyświetlaj szczegółowe komunikaty')

    return parser.parse_args()


def main():
    """
    Główna funkcja skryptu.

    Returns:
        int: Kod zakończenia (0 - sukces, 1 - błąd)
    """
    # Parsuj argumenty
    args = parse_arguments()

    # Ustaw poziom logowania
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        # Sprawdź czy plik wejściowy istnieje
        if not os.path.isfile(args.input_file):
            logger.error(f"Plik wejściowy nie istnieje: {args.input_file}")
            return 1

        # Sprawdź rozszerzenie pliku
        is_pdf = args.input_file.lower().endswith('.pdf')

        # Jeśli wybrano opcję przycinania i plik to PDF, użyj funkcji trim_existing_pdf
        if args.trim_only and is_pdf:
            logger.info(
                f"Tryb przycinania istniejącego PDF: {args.input_file}")

            output_path = args.output if args.output else args.input_file
            result = trim_existing_pdf(args.input_file, output_path)

            if result:
                logger.info(f"Pomyślnie przycięto PDF: {result}")
                return 0
            else:
                logger.error("Nie udało się przyciąć PDF")
                return 1

        # Jeśli to PDF, ale nie wybrano trybu przycinania, wyświetl informację
        if is_pdf and not args.trim_only:
            logger.warning(
                "Podano plik PDF jako wejściowy, ale nie wybrano trybu przycinania (--trim-only)")
            logger.warning("Przechodzę do przycinania istniejącego PDF...")

            output_path = args.output if args.output else args.input_file
            result = trim_existing_pdf(args.input_file, output_path)

            if result:
                logger.info(f"Pomyślnie przycięto PDF: {result}")
                return 0
            else:
                logger.error("Nie udało się przyciąć PDF")
                return 1

        # Jeśli podano liczbę pozycji, wyświetl informację
        if args.items:
            logger.info(f"Używam podanej liczby pozycji: {args.items}")
            # Obliczmy i wyświetlmy optymalną wysokość
            optimal_height = calculate_optimal_height(
                args.input_file, args.items)
            logger.info(f"Optymalna wysokość dokumentu: {optimal_height}mm")

        # Konwersja HTML do PDF
        temp_pdf = html_to_pdf_continuous(
            args.input_file,
            None,  # Najpierw generuj do pliku tymczasowego
            args.width,
            args.margin,
            args.dpi,
            not args.single_pass  # Używaj dwuprzebiegowego podejścia, chyba że podano --single-pass
        )

        # Jeśli wybrano opcję podziału PDF
        if args.split_pdf and temp_pdf:
            try:
                # Podziel PDF na część z treścią i białą przestrzenią
                content_height, content_path, blank_path = split_pdf_at_content_end(
                    temp_pdf, None, None
                )

                if content_height and content_path:
                    logger.info(
                        f"Podzielono PDF. Wysokość treści: {content_height:.2f}mm")
                    logger.info(f"Treść zapisana do: {content_path}")
                    logger.info(f"Biała przestrzeń zapisana do: {blank_path}")

                    # Użyj treści jako finalnego PDF
                    temp_pdf = content_path
                else:
                    logger.warning(
                        "Nie można podzielić PDF - używam pełnego dokumentu")
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

        logger.info(
            f"Konwersja zakończona pomyślnie. Wygenerowano plik: {final_pdf}")
        return 0

    except Exception as e:
        logger.error(f"Wystąpił błąd: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def copy_pdf():
    """
    Copy ZO_0024_25.pdf.bak to ZO_0024_25.pdf
    """
    source_file = 'ZO_0024_25.copy.pdf'
    destination_file = 'ZO_0024_25.pdf'

    try:
        # Check if source file exists
        if not os.path.exists(source_file):
            print(f"Error: Source file {source_file} does not exist.")
            return False

        # Copy the file
        shutil.copy2(source_file, destination_file)

        print(f"Successfully copied {source_file} to {destination_file}")
        return True

    except Exception as e:
        print(f"An error occurred while copying the file: {e}")
        return False


if __name__ == "__main__":
    copy_pdf()
    sys.exit(main())


# python html_to_pdf_cont.py ZO_0024_25.pdf --width 4.0 --margin 1 --dpi 203 --trim-only
#
