#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import win32print
import tempfile
import os
import requests
import tempfile
import os
import win32print
import win32ui
from PIL import Image, ImageWin


def print_zpl_as_image_to_windows(zpl_content, printer_name=None):
    """Convert ZPL to an image and print to Windows printer"""
    # If no printer specified, use default
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()

    # Use Labelary API to convert ZPL to PNG
    url = "http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/"
    headers = {"Accept": "image/png"}
    response = requests.post(url, headers=headers, data=zpl_content.encode('utf-8'))

    if response.status_code != 200:
        print(f"Error converting ZPL to image: {response.status_code}")
        return

    # Save the image to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file.write(response.content)
    temp_file.close()

    try:
        # Create a device context for the printer
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)

        # Get the printer capabilities
        printer_size = hDC.GetDeviceCaps(110), hDC.GetDeviceCaps(111)

        # Open the image
        img = Image.open(temp_file.name)

        # Start the print job
        hDC.StartDoc(temp_file.name)
        hDC.StartPage()

        # Convert the image to a DIB and print it
        dib = ImageWin.Dib(img)
        dib.draw(hDC.GetHandleOutput(), (0, 0, printer_size[0], printer_size[1]))

        # Finish the print job
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()

        print(f"Print job (as image) sent to {printer_name}")
    except Exception as e:
        print(f"Error printing image: {e}")
    finally:
        # Clean up the temporary file
        os.unlink(temp_file.name)



def print_zpl_to_windows_printer(zpl_content, printer_name=None):
    """Print ZPL content directly to a Windows printer"""
    # If no printer specified, use default
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()

    # Create a temporary file with the ZPL content
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zpl')
    temp_file.write(zpl_content.encode('utf-8'))
    temp_file.close()

    try:
        # Open the printer
        handle = win32print.OpenPrinter(printer_name)
        try:
            # Start a document
            job = win32print.StartDocPrinter(handle, 1, ("ZPL Document", None, "RAW"))
            try:
                # Start a page
                win32print.StartPagePrinter(handle)

                # Write the ZPL content directly to the printer
                with open(temp_file.name, 'rb') as f:
                    data = f.read()
                    win32print.WritePrinter(handle, data)

                # End the page
                win32print.EndPagePrinter(handle)
            finally:
                # End the document
                win32print.EndDocPrinter(handle)
        finally:
            # Close the printer
            win32print.ClosePrinter(handle)

        print(f"Print job sent to {printer_name}")
    except Exception as e:
        print(f"Error printing: {e}")
    finally:
        # Clean up the temporary file
        os.unlink(temp_file.name)


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import win32print
import win32api
import tempfile
import os


def create_label_pdf(output_path):
    c = canvas.Canvas(output_path, pagesize=(288, 432))  # 4x6 inches at 72dpi

    # Add text
    c.setFont("Helvetica", 12)
    c.drawString(36, 396, "Nr dokumentu: FAK 1234/2025")
    c.drawString(36, 372, "Kontrahent: MegaSklep - Siedlce")
    c.drawString(36, 348, "Wartość: 3826.68 PLN")
    c.drawString(36, 324, "Data: 2025-03-22")

    # Add barcode (using reportlab's built-in barcode)
    from reportlab.graphics.barcode import code128
    barcode = code128.Code128("123456789012", barHeight=50)
    barcode.drawOn(c, 36, 250)
    c.drawString(36, 225, "123456789012")

    c.save()


def print_pdf_to_windows_printer(pdf_path, printer_name=None):
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()

    try:
        win32api.ShellExecute(
            0,
            "print",
            pdf_path,
            f'/d:"{printer_name}"',
            ".",
            0
        )
        print(f"PDF print job sent to {printer_name}")
    except Exception as e:
        print(f"Error printing PDF: {e}")


def printaspdf(zpl_content):
    # Create and print a label
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.close()

    create_label_pdf(temp_file.name)
    print_pdf_to_windows_printer(temp_file.name)

    # Clean up temporary file after a delay to allow printer
    import time

    time.sleep(5)
    os.unlink(temp_file.name)

# Your ZPL content
zpl_content = """^XA
^CI28
^FO50,50^A0N,30,30^FDNr dokumentu: FAK 1234/2025^FS
^FO50,90^A0N,30,30^FDKontrahent: MegaSklep - Siedlce^FS
^FO50,130^A0N,30,30^FDWartość: 3826.68 PLN^FS
^FO50,170^A0N,30,30^FDData: 2025-03-22^FS
^FO50,240^BY3
^BCN,100,Y,N,N
^FD123456789012^FS
^FO50,360^A0N,20,20^FD123456789012^FS
^XZ"""

# Print to the default Windows printer
#print_zpl_to_windows_printer(zpl_content)
# Print to the default Windows printer as an image
print_zpl_as_image_to_windows(zpl_content)

# Optionally, specify a printer by name
# print_zpl_to_windows_printer(zpl_content, "Zebra ZT411")