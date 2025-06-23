#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from bs4 import BeautifulSoup
import socket
import re

# Try to import win32print for Windows printer
try:
    import win32print

    WINDOWS_PRINTING = True
except ImportError:
    WINDOWS_PRINTING = False


def html_to_zpl(html_file, label_width):
    """
    Convert HTML order data to ZPL format

    Args:
        html_file (str): Path to HTML file
        label_width (int): Width of the label in dots

    Returns:
        str: ZPL formatted data
    """
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except FileNotFoundError:
        print(f"Error: File {html_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract order data
    order_number = soup.find("div", class_="title").text.strip() if soup.find("div",
                                                                              class_="title") else "Unknown Order"
    order_date = soup.find("div", class_="date").text.strip(
    ) if soup.find("div", class_="date") else ""

    # Extract client information
    client_rows = soup.find_all("div", class_="client-row")
    client_info = {}
    for row in client_rows:
        label_div = row.find("div", class_="client-label")
        if label_div:
            label = label_div.text.strip()
            value = label_div.find_next_sibling("div").text.strip(
            ) if label_div.find_next_sibling("div") else ""
            client_info[label] = value

    # Extract items from table
    items = []
    rows = soup.select("table tbody tr")
    for row in rows:
        cells = row.find_all("td")
        if cells and len(cells) >= 8:
            item = {
                "name": cells[1].text.strip(),
                "quantity": cells[2].text.strip(),
                "unit": cells[3].text.strip(),
                "price": cells[6].text.strip().replace('\n', '/'),
                "value": cells[7].text.strip().replace('\n', '/')
            }
            items.append(item)

    # Extract totals
    total_rows = soup.select("table tfoot tr")
    totals = {}
    for row in total_rows:
        label_cell = row.find_all("td")[-2]
        value_cell = row.find_all("td")[-1]
        if label_cell and value_cell:
            totals[label_cell.text.strip()] = value_cell.text.strip()

    # Generate ZPL code
    zpl = []
    zpl.append("^XA")  # Start format

    # Set label dimensions
    zpl.append(f"^PW{label_width}")  # Label width in dots

    # Header with order number and date
    y_pos = 20
    zpl.append(f"^FO20,{y_pos}^A0N,30,30^FD{order_number}^FS")
    y_pos += 40
    zpl.append(f"^FO20,{y_pos}^A0N,20,20^FD{order_date}^FS")
    y_pos += 30

    # Client information
    zpl.append(f"^FO20,{y_pos}^A0N,25,25^FDInformacje o kliencie:^FS")
    y_pos += 30

    for label, value in client_info.items():
        if label in ["Zamawiający", "Adres", "NIP"]:
            zpl.append(f"^FO20,{y_pos}^A0N,20,20^FD{label}: {value}^FS")
            y_pos += 25

    # Table header
    y_pos += 20
    zpl.append(f"^FO20,{y_pos}^A0N,25,25^FDZamówione produkty:^FS")
    y_pos += 30

    # Table column headers
    zpl.append(f"^FO20,{y_pos}^A0N,20,20^FDLp.^FS")
    zpl.append(f"^FO60,{y_pos}^A0N,20,20^FDNazwa^FS")
    zpl.append(f"^FO{label_width - 300},{y_pos}^A0N,20,20^FDIlość^FS")
    zpl.append(f"^FO{label_width - 200},{y_pos}^A0N,20,20^FDCena^FS")
    zpl.append(f"^FO{label_width - 100},{y_pos}^A0N,20,20^FDWartość^FS")
    y_pos += 25

    # Horizontal line
    zpl.append(f"^FO20,{y_pos}^GB{label_width - 40},3,3^FS")
    y_pos += 10

    # Table rows
    for i, item in enumerate(items, 1):
        zpl.append(f"^FO20,{y_pos}^A0N,20,20^FD{i}^FS")
        zpl.append(f"^FO60,{y_pos}^A0N,20,20^FD{item['name']}^FS")
        zpl.append(
            f"^FO{label_width - 300},{y_pos}^A0N,20,20^FD{item['quantity']} {item['unit']}^FS")
        zpl.append(
            f"^FO{label_width - 200},{y_pos}^A0N,20,20^FD{item['price']}^FS")
        zpl.append(
            f"^FO{label_width - 100},{y_pos}^A0N,20,20^FD{item['value']}^FS")
        y_pos += 25

    # Horizontal line
    y_pos += 5
    zpl.append(f"^FO20,{y_pos}^GB{label_width - 40},3,3^FS")
    y_pos += 15

    # Totals
    for label, value in totals.items():
        zpl.append(f"^FO{label_width - 350},{y_pos}^A0N,25,25^FD{label}:^FS")
        zpl.append(f"^FO{label_width - 100},{y_pos}^A0N,25,25^FD{value}^FS")
        y_pos += 30

    # QR code with order number
    y_pos += 10
    order_id = re.search(r'ZO\s+(\d+/\d+)', order_number)
    qr_data = order_id.group(1) if order_id else "Unknown"
    zpl.append(f"^FO20,{y_pos}^BQN,2,6^FD{qr_data}^FS")

    # End format
    zpl.append("^XZ")

    return "\n".join(zpl)


def print_to_zebra(zpl_data, printer_name, port=9100):
    """
    Send ZPL data to a Zebra printer

    Args:
        zpl_data (str): ZPL data to print
        printer_name (str): Printer name or IP address
        port (int): Printer port, default is 9100
    """
    # Check if we're on Windows
    if sys.platform.startswith('win'):
        try:
            # Try to print using the Windows printer system
            import win32print

            # Get the default printer if none specified
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()

            # Open printer
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                # Start a document
                hJob = win32print.StartDocPrinter(
                    hPrinter, 1, ("ZPL Document", None, "RAW"))
                try:
                    # Start a page
                    win32print.StartPagePrinter(hPrinter)
                    # Write the ZPL data
                    win32print.WritePrinter(hPrinter, zpl_data.encode('utf-8'))
                    # End the page
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    # End the document
                    win32print.EndDocPrinter(hPrinter)
            finally:
                # Close the printer
                win32print.ClosePrinter(hPrinter)

            print("Successfully sent data to printer using Windows printer system")
            return
        except ImportError:
            print("win32print module not found, falling back to socket printer")
        except Exception as e:
            print(f"Error using Windows printer: {e}")
            print("Falling back to socket printer")

    # Socket printer (for IP printers or as fallback)
    try:
        # Check if printer_name looks like an IP address
        ip_pattern = r'^\d+\.\d+\.\d+\.\d+$'
        if not re.match(ip_pattern, printer_name):
            print(
                f"Warning: '{printer_name}' doesn't look like an IP address. Socket printer may fail.")
            print(
                "If this is a local printer, try installing the win32print module: pip install pywin32")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((printer_name, port))
        s.send(zpl_data.encode('utf-8'))
        s.close()
        print("Successfully sent data to printer using socket")
    except Exception as e:
        print(f"Error sending data to printer: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Print HTML order to ZPL format')
    parser.add_argument('html_file', help='Path to HTML file')
    parser.add_argument('printer_name', help='Printer name or IP address')
    parser.add_argument('--width', type=int, default=800,
                        help='Label width in dots (default: 800)')
    parser.add_argument('--save', action='store_true', help='Save ZPL to file')
    parser.add_argument('--port', type=int, default=9100,
                        help='Printer port (default: 9100)')
    parser.add_argument('--list-printers', action='store_true',
                        help='List available Windows printers and exit')
    args = parser.parse_args()

    # List printers if requested
    if args.list_printers:
        if WINDOWS_PRINTING:
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            print("Available printers:")
            for printer in printers:
                print(f" - {printer[2]}")
            print(f"Default printer: {win32print.GetDefaultPrinter()}")
        else:
            print("win32print module not available. Install pywin32 to list printers.")
        sys.exit(0)

    # Convert HTML to ZPL
    zpl_data = html_to_zpl(args.html_file, args.width)

    # Print to Zebra printer
    print_to_zebra(zpl_data, args.printer_name, args.port)

    # Optionally save ZPL to file
    if args.save:
        output_file = os.path.splitext(args.html_file)[0] + ".zpl"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(zpl_data)
        print(f"ZPL data saved to {output_file}")


if __name__ == "__main__":
    main()


# python html2zpl2print.py zamowienie.html "ZDesigner GK420d" --width 300 --save

# python html2zpl2print.py zamowienie.html "ZDesigner GK420d" --width 800 --save
# python html2zpl2print.py zamowienie.html "Zebra_Z_4" --width 800 --save
# python zpl30cm.py "ZDesigner GK420d"
