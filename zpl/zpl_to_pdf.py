import requests
import tempfile
import os
import sys
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import argparse


def convert_zpl_to_image(zpl_content, dpmm=8):
    """Convert ZPL content to PNG image using Labelary API"""
    url = f"http://api.labelary.com/v1/printers/{dpmm}dpmm/labels/4x6/0/"

    # Dodanie nagłówka charset=utf-8 dla poprawnej obsługi polskich znaków
    headers = {
        "Accept": "image/png",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
    }

    # Sprawdź, czy zpl_content zawiera ^CI, jeśli nie, dodaj ^CI28 na początku
    if not "^CI" in zpl_content and zpl_content.startswith("^XA"):
        parts = zpl_content.split("^XA", 1)
        zpl_content = parts[0] + "^XA^CI28" + parts[1]

    try:
        # Upewniamy się, że wysyłamy dane w UTF-8
        response = requests.post(url, headers=headers, data=zpl_content.encode('utf-8'))
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error converting ZPL to image: {e}")
        return None


def image_to_pdf(image_data, output_path):
    """Convert PNG image data to PDF file"""
    # Save the image to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file.write(image_data)
    temp_filename = temp_file.name
    temp_file.close()

    try:
        # Create a PDF with the image
        from reportlab.lib.utils import ImageReader
        from PIL import Image

        # Get image dimensions
        img = Image.open(temp_filename)
        img_width, img_height = img.size

        # Create PDF with appropriate size
        c = canvas.Canvas(output_path, pagesize=(img_width, img_height))
        c.drawImage(ImageReader(temp_filename), 0, 0, width=img_width, height=img_height)
        c.save()

        # Ważne: zamknij obiekt Image przed próbą usunięcia pliku
        img.close()

        print(f"PDF created successfully at: {output_path}")
        return True, output_path  # Zwracamy krotkę z sukcesem i ścieżką
    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False, None  # Zwracamy krotkę z porażką i None
    finally:
        # Próba usunięcia pliku tymczasowego z obsługą błędów
        try:
            # Dłuższe opóźnienie, aby dać systemowi czas na zwolnienie pliku
            time.sleep(0.5)  # Zwiększ opóźnienie
            os.unlink(temp_filename)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_filename}: {e}")
            # Utworzenie zadania do późniejszego usunięcia pliku
            try:
                if sys.platform == 'win32':
                    os.system(f'(ping 127.0.0.1 -n 2 > nul && del "{temp_filename}" > nul 2>&1)')
                else:
                    os.system(f'(sleep 2 && rm "{temp_filename}") &')
            except:
                pass


def convert_zpl_file_to_pdf(input_file, output_file=None, dpmm=8, args_print=False):
    """Convert a ZPL file to PDF"""
    # If no output file specified, create one with the same name but .pdf extension
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.pdf'

    try:
        # Read the ZPL file with UTF-8 encoding dla poprawnej obsługi polskich znaków
        with open(input_file, 'r', encoding='utf-8') as f:
            zpl_content = f.read()

        # Convert to image
        image_data = convert_zpl_to_image(zpl_content, dpmm)
        if image_data:
            # Convert image to PDF
            success, actual_output = image_to_pdf(image_data, output_file)
            if success and args_print and actual_output:
                print_pdf(actual_output)
            return success
    except Exception as e:
        print(f"Error processing file {input_file}: {e}")

    return False


def convert_zpl_string_to_pdf(zpl_content, output_file, dpmm=8):
    """Convert a ZPL string to PDF"""
    # Convert to image
    image_data = convert_zpl_to_image(zpl_content, dpmm)
    if image_data:
        # Convert image to PDF
        success, actual_output = image_to_pdf(image_data, output_file)
        return success
    return False


def print_pdf(pdf_path):
    """Print a PDF file to the default printer"""
    if sys.platform == 'win32':
        try:
            import win32print
            import win32api

            printer_name = win32print.GetDefaultPrinter()
            win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
            print(f"Print job sent to {printer_name}")
            return True
        except ImportError:
            print("pywin32 not installed. Cannot print on Windows without it.")
            return False
        except Exception as e:
            print(f"Error printing PDF: {e}")
            return False
    else:
        try:
            import subprocess
            result = subprocess.run(['lp', pdf_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("Print job sent to default printer")
                return True
            else:
                print(f"Error printing: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error printing PDF: {e}")
            return False


def create_label_pdf_direct(output_path, data):
    """Create PDF label directly using ReportLab without ZPL"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import barcode
    from barcode.writer import ImageWriter

    # Register a font with Polish characters support
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    # Create canvas
    c = canvas.Canvas(output_path, pagesize=(400, 300))
    c.setFont('DejaVuSans', 12)

    # Add text
    c.drawString(50, 250, f"Nr dokumentu: {data['nr_dokumentu']}")
    c.drawString(50, 230, f"Kontrahent: {data['kontrahent']}")
    c.drawString(50, 210, f"Wartość: {data['wartosc']} PLN")
    c.drawString(50, 190, f"Data: {data['data']}")

    # Add barcode
    code128 = barcode.get('code128', data['barcode'], writer=ImageWriter())
    filename = code128.save('temp_barcode')
    c.drawImage(filename, 50, 100, width=200, height=70)

    c.save()
    return True

def main():
    parser = argparse.ArgumentParser(description="Convert ZPL files to PDF and optionally print them")
    parser.add_argument("input", help="Input ZPL file path or ZPL string")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    parser.add_argument("-d", "--dpmm", type=int, default=8, help="Dots per mm (default: 8)")
    parser.add_argument("-p", "--print", action="store_true", help="Print the PDF after creating it")
    parser.add_argument("-s", "--string", action="store_true", help="Treat input as ZPL string instead of file path")

    args = parser.parse_args()

    # Set default output if not specified
    if not args.output and not args.string:
        args.output = os.path.splitext(args.input)[0] + '.pdf'
    elif not args.output and args.string:
        args.output = "label.pdf"

    # Convert ZPL to PDF
    if args.string:
        success = convert_zpl_string_to_pdf(args.input, args.output, args.dpmm)
    else:
        success = convert_zpl_file_to_pdf(args.input, args.output, args.dpmm, args.print)

    # Print if requested and conversion was successful
    if success and args.print:
        print_pdf(args.output)


# Example usage in code
if __name__ == "__main__":
    main()

    # Sample ZPL for testing within the script - with Polish characters

    # Zakomentuj poniższe linie, aby uniknąć wykonania przy importowaniu
    # convert_zpl_string_to_pdf(sample_zpl, "output.pdf")
    # print_pdf("output.pdf")