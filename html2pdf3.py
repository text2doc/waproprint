#!/usr/bin/env python
# -*- coding: utf-8 -*-
# html2pdf3.py

import asyncio
from playwright.async_api import async_playwright
import socket
import tempfile
import os
import re
import os
import sys
import logging
from html2text import HTML2Text
from playwright.async_api import async_playwright

# Windows-specific imports
try:
    import win32print
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    if sys.platform == 'win32':
        logging.warning("pywin32 is not installed. Windows printing functionality will be disabled.")
    else:
        logging.info("Non-Windows platform detected. Windows printing functionality is not available.")


async def print_to_zebra_printer(url, printer_name=None, connection_type="windows",
                                 network_args=None, label_width_mm=104, label_height_mm=150):
    """
    Drukuje stronę HTML na drukarce Zebra konwertując treść do formatu ZPL.

    Parametry:
    - url: URL strony do wydrukowania lub ścieżka do pliku HTML
    - printer_name: Nazwa drukarki (dla Windows, jeśli None, zostanie użyta domyślna)
    - connection_type: Typ połączenia z drukarką ('windows', 'network', 'file')
    - network_args: Argumenty dla połączenia sieciowego (słownik: {'host', 'port'})
    - label_width_mm: Szerokość etykiety w milimetrach
    - label_height_mm: Wysokość etykiety w milimetrach

    Zwraca:
    - True jeśli drukowanie zakończyło się powodzeniem, False w przeciwnym przypadku
    """
    try:
        # 1. Pobierz zawartość strony HTML za pomocą Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Ustaw wymiary strony na wymiary etykiety
            width_px = int(label_width_mm * 3.78)  # Przybliżona konwersja mm na px (96 DPI)
            height_px = int(label_height_mm * 3.78)
            await page.set_viewport_size({"width": width_px, "height": height_px})

            # Jeśli URL jest ścieżką lokalną, dostosuj
            if os.path.exists(url):
                url = f"file://{os.path.abspath(url)}"

            await page.goto(url)

            # Dodaj style CSS, aby dostosować do drukarki Zebra
            await page.add_style_tag(content=f"""
                @media print {{
                    body, html {{
                        width: 100%;
                        margin: 0 !important;
                        padding: 0 !important;
                        page-break-after: avoid !important;
                        page-break-before: avoid !important;
                    }}
                    * {{
                        page-break-inside: avoid !important;
                    }}
                    @page {{
                        size: {label_width_mm}mm auto;
                        margin: 0mm !important;
                        padding: 0mm !important;
                    }}
                }}
            """)

            # 2. Pobierz zawartość HTML
            html_content = await page.content()

            # 3. Konwertuj HTML na ZPL
            zpl_code = html_to_zpl(html_content, label_width_mm, label_height_mm)

            # 4. Drukuj w zależności od wybranej metody połączenia
            if connection_type == "windows":
                # Metoda Windows (win32print)
                return print_windows_raw(zpl_code, printer_name)

            elif connection_type == "network" and network_args:
                # Metoda sieciowa (bezpośrednie połączenie z drukarką)
                return print_network_raw(zpl_code, network_args)

            elif connection_type == "file":
                # Zapisz do pliku (użyteczne do debugowania)
                with open("zebra_print.zpl", "w", encoding="utf-8") as f:
                    f.write(zpl_code)
                return True

            else:
                print("Nieprawidłowy typ połączenia lub brakujące argumenty")
                return False

            await browser.close()

    except Exception as e:
        print(f"Wystąpił błąd podczas drukowania: {e}")
        return False


def html_to_zpl(html_content, width_mm=104, height_mm=150, dpi=203):
    """
    Konwertuje zawartość HTML na kod ZPL.

    Parametry:
    - html_content: Zawartość HTML do konwersji
    - width_mm: Szerokość etykiety w mm
    - height_mm: Wysokość etykiety w mm
    - dpi: Rozdzielczość drukarki (typowo 203 DPI dla drukarek Zebra)

    Zwraca:
    - Kod ZPL gotowy do wysłania do drukarki
    """
    # Konwertuj HTML na prosty tekst
    h = HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.ignore_tables = False
    h.single_line_break = True
    plain_text = h.handle(html_content)

    # Usuń zbędne znaczniki markdown
    plain_text = re.sub(r'#+ ', '', plain_text)  # Usuń nagłówki markdown
    plain_text = re.sub(r'\*\*', '', plain_text)  # Usuń pogrubienia
    plain_text = re.sub(r'\*', '', plain_text)  # Usuń kursywę
    plain_text = plain_text.replace('\\', '')  # Usuń escapowane znaki

    # Podziel tekst na linie
    lines = plain_text.strip().split('\n')

    # Konwertuj jednostki na punkty (dots)
    dots_per_mm = dpi / 25.4
    width_dots = int(width_mm * dots_per_mm)
    height_dots = int(height_mm * dots_per_mm)

    # Generuj kod ZPL
    zpl = "^XA"  # Rozpoczęcie formatu etykiety

    # Ustaw rozmiar etykiety i orientację
    zpl += f"^PW{width_dots}"  # Szerokość wydruku

    # Ustawienia główne
    zpl += "^LH0,0"  # Początek etykiety (lewy górny róg)
    zpl += "^CI28"  # Kodowanie znaków (UTF-8)

    # Konwertuj zawartość tekstową na elementy ZPL
    y_position = 30  # Początkowa pozycja Y

    for line in lines:
        if line.strip():
            # Dodaj pole tekstowe
            zpl += f"^FO20,{y_position}"  # Pozycja pola (x,y)
            zpl += "^A0N,20,20"  # Czcionka (czcionka 0, normalna, wysokość 20, szerokość 20)
            zpl += f"^FD{line.strip()}^FS"  # Dane pola i zakończenie pola
            y_position += 30  # Odstęp między liniami

    zpl += "^XZ"  # Zakończenie formatu etykiety
    return zpl


def print_windows_raw(zpl_code, printer_name=None):
    """Drukuje surowy kod ZPL na drukarce Windows"""
    try:
        # Jeśli nie podano nazwy drukarki, użyj domyślnej
        if printer_name is None:
            printer_name = win32print.GetDefaultPrinter()

        # Otwórz uchwyt do drukarki
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            # Rozpocznij dokument
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("ZPL Document", None, "RAW"))
            try:
                # Rozpocznij stronę
                win32print.StartPagePrinter(hPrinter)
                # Wyślij surowe dane ZPL
                win32print.WritePrinter(hPrinter, zpl_code.encode('utf-8'))
                # Zakończ stronę
                win32print.EndPagePrinter(hPrinter)
            finally:
                # Zakończ dokument
                win32print.EndDocPrinter(hPrinter)
        finally:
            # Zamknij uchwyt drukarki
            win32print.ClosePrinter(hPrinter)
        return True

    except Exception as e:
        print(f"Błąd drukowania w systemie Windows: {e}")
        return False


def print_network_raw(zpl_code, network_args):
    """Wysyła surowy kod ZPL bezpośrednio do drukarki sieciowej"""
    try:
        host = network_args.get('host', '192.168.1.100')
        port = network_args.get('port', 9100)

        # Nawiąż połączenie z drukarką
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))

        # Wyślij kod ZPL
        s.sendall(zpl_code.encode('utf-8'))

        # Zamknij połączenie
        s.close()
        return True

    except Exception as e:
        print(f"Błąd drukowania przez sieć: {e}")
        return False


from lib.ConfigManager import ConfigManager
config = ConfigManager()
zpl_dir = config.get_zo_zpl_dir()
# Pobierz parametry drukarki z konfiguracji
printer_name = config.get_thermal_printer_name()
dpi = config.get_printer_dpi()
label_margin = config.get_printer_label_margin()
label_width = config.get_printer_label_width()
label_height = config.get_printer_label_height()
font_size = config.get_printer_font_size()
encoding = config.get_printer_encoding()


async def html_to_pdf(url, output_path=None, label_width_mm=104, continuous=True,
                      margins=None, timeout=30000, css_styles=None,
                      wait_for_selectors=None, print_background=True, dpi=203):
    """
    Konwertuje stronę HTML do formatu PDF dostosowanego do drukarki termicznej.

    Parametry:
    - url: URL strony do konwersji lub ścieżka do pliku HTML
    - output_path: Ścieżka wyjściowa dla pliku PDF (domyślnie: 'output.pdf')
    - label_width_mm: Szerokość etykiety/wydruku w milimetrach (domyślnie: 104 mm)
    - continuous: Tryb drukowania ciągłego bez podziału na strony (bool)
    - margins: Marginesy strony w mm (słownik: {"top": 0, "right": 0, "bottom": 0, "left": 0})
    - timeout: Timeout w milisekundach dla ładowania strony
    - css_styles: Dodatkowe style CSS dla strony
    - wait_for_selectors: Lista selektorów CSS, na które trzeba poczekać przed generowaniem PDF
    - print_background: Czy uwzględniać tła podczas drukowania (bool)
    - dpi: Rozdzielczość drukarki w DPI (typowo 203 DPI dla drukarek termicznych)

    Zwraca:
    - Ścieżkę do wygenerowanego pliku PDF lub None w przypadku błędu
    """
    try:

        # Ustaw domyślną nazwę pliku wyjściowego, jeśli nie została podana
        if output_path is None:
            output_path = "output.pdf"

        # Ustaw domyślne marginesy, jeśli nie zostały podane (dla drukarek termicznych zwykle zerowe)
        if margins is None:
            margins = {"top": 0, "right": 0, "bottom": 0, "left": 0}

        # Ustaw domyślne style CSS dla drukarki termicznej
        default_css = f"""
            @page {{
                size: {label_width_mm}mm auto !important;
                margin: 0mm !important;
                padding: 0mm !important;
            }}
            html, body {{
                width: {label_width_mm}mm !important;
                margin: 0 !important;
                padding: 0 !important;
                background-color: white;
                color: black;
                line-height: 1.2;
            }}
            * {{
                page-break-inside: avoid !important;
                page-break-before: avoid !important;
                page-break-after: avoid !important;
                box-sizing: border-box !important;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            td, th {{
                padding: 2px;
            }}
            img {{
                max-width: 100%;
            }}
        """

        css_to_inject = default_css
        if css_styles:
            css_to_inject += css_styles

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Jeśli URL jest ścieżką lokalną, dostosuj
            if os.path.exists(url):
                url = f"file://{os.path.abspath(url)}"

            # Przejdź do strony
            await page.goto(url, wait_until="networkidle", timeout=timeout)

            # Dodaj style CSS
            await page.add_style_tag(content=css_to_inject)

            # Dodaj dodatkowe style CSS, aby wymusić ciągły wydruk bez paginacji
            await page.add_style_tag(content=f"""
                @media print {{
                    body, html {{
                        width: 100%;
                        margin: 0 !important;
                        padding: 0 !important;
                        page-break-after: avoid !important;
                        page-break-before: avoid !important;
                    }}
                    * {{
                        page-break-inside: avoid !important;
                    }}
                    @page {{
                        size: {label_width_mm}mm auto;
                        margin: 0mm !important;
                        padding: 0mm !important;
                    }}
                }}
            """)

            # Poczekaj, aż strona będzie w pełni załadowana
            await page.wait_for_load_state("networkidle")

            # Jeśli są określone selektory, poczekaj na nie
            if wait_for_selectors:
                for selector in wait_for_selectors:
                    await page.wait_for_selector(selector, timeout=timeout)

            # Uzyskaj rzeczywistą wysokość zawartości strony
            height_js = """
                Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.offsetHeight
                )
            """
            content_height = await page.evaluate(height_js)

            # Konwertuj mm na px używając podanego DPI
            width_px = int(label_width_mm * dpi / 25.4)  # Konwersja mm na px przy danym DPI

            # Ustaw wymiary viewportu żeby dopasować je do szerokości etykiety
            await page.set_viewport_size({"width": width_px, "height": content_height})

            # Przygotuj marginesy jako ciągi znaków z jednostkami
            formatted_margins = {
                "top": "0mm",
                "right": "0mm",
                "bottom": "0mm",
                "left": "0mm"
            }

            # Przygotuj parametry do drukowania PDF dla drukarki termicznej z prawidłowymi nazwami parametrów
            pdf_options = {
                "path": output_path,
                "width": f"{label_width_mm}mm",
                "height": f"{content_height}px" if continuous else None,
                "print_background": print_background,
                "margin": formatted_margins,
                "display_header_footer": False,  # Bez nagłówków i stopek
                "prefer_css_page_size": True,
                "scale": 1.0,
                "page_ranges": ""  # Puste oznacza wszystkie strony
            }

            # Usuń None wartości z parametrów
            pdf_options = {k: v for k, v in pdf_options.items() if v is not None}

            # Generuj PDF
            await page.pdf(**pdf_options)

            # Opcjonalnie: Po utworzeniu PDF możemy sprawdzić, czy plik zawiera paginację
            # i wykonać dodatkowe kroki, jeśli to konieczne

            await browser.close()

            # Sprawdź czy plik został utworzony
            if os.path.exists(output_path):
                # Tutaj można dodać dodatkowe sprawdzenie PDF z użyciem np. PyPDF2 lub podobnej biblioteki
                # aby upewnić się, że nie ma paginacji
                try:
                    # Jeśli chcesz sprawdzić plik PDF, możesz odkomentować poniższy kod
                    # i zainstalować bibliotekę PyPDF2
                    """
                    import PyPDF2
                    with open(output_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        if len(pdf_reader.pages) > 1:
                            print("Ostrzeżenie: Wygenerowany PDF ma więcej niż jedną stronę!")
                    """
                    return output_path
                except Exception as e:
                    print(f"Uwaga: Nie można zweryfikować poprawności pliku PDF: {e}")
                    return output_path
            return None

    except Exception as e:
        print(f"Wystąpił błąd podczas konwersji HTML do PDF: {e}")
        return None




# Przykład użycia:
import asyncio

async def main():
    pdf_path = await html_to_pdf(
        url="zamowienie.html",
        output_path="zamowienie.pdf",
        label_width_mm=104,  # Szerokość drukarki termicznej 104mm
        continuous=True,  # Tryb ciągły bez podziału na strony
        margins={"top": 0, "right": 0, "bottom": 0, "left": 0},
        css_styles="body { font-size: 14px; line-height: 1.2; } img { max-width: 100%; }"
    )

    if pdf_path:
        print(f"PDF dla drukarki termicznej został wygenerowany: {pdf_path}")
    else:
        print("Nie udało się wygenerować PDF")

# Uruchomienie przykładu
# asyncio.run(main())




# Przykład użycia:
import asyncio

async def main3():
    pdf_path = await html_to_pdf(
        url="zamowienie.html",
        output_path="zamowienie.pdf",
        page_size="A4",
        orientation="portrait",
        margins={"top": 20, "right": 20, "bottom": 20, "left": 20},
        css_styles="body { font-size: 14px; line-height: 1.5; }"
    )

    if pdf_path:
        print(f"PDF został wygenerowany: {pdf_path}")
    else:
        print("Nie udało się wygenerować PDF")

# Uruchomienie przykładu
# asyncio.run(main())

# zebra_print.zpl
# Przykład użycia:
async def main2():
    success = await print_to_zebra_printer(
        "zamowienie.html",
        printer_name=printer_name,  # Nazwa twojej drukarki Zebra
        connection_type="file",  # Użycie API Windows
        label_width_mm=104  # Szerokość etykiety
        #label_height_mm=150  # Wysokość etykiety
    )

    if success:
        print("Drukowanie zakończone sukcesem")
    else:
        print("Wystąpił błąd podczas drukowania")


if __name__ == "__main__":
    asyncio.run(main())


# python html2pdf3.py