import requests
import tempfile


def simple_convert(zpl_content, output_file):
    url = "http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/"
    headers = {
        "Accept": "application/pdf",  # Żądamy bezpośrednio PDF zamiast PNG
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
    }

    response = requests.post(url, headers=headers,
                             data=zpl_content.encode('utf-8'))

    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"PDF saved to {output_file}")
        return True
    else:
        print(f"Error: {response.status_code}")
        return False


# Przykładowy kod ZPL
zpl = """^XA
^CI28
^FO50,50^A0N,30,30^FDNr dokumentu: FAK 1234/2025^FS
^FO50,90^A0N,30,30^FDKontrahent: Test Polish^FS
^FO50,130^A0N,30,30^FDWartość: 3826.68 PLN^FS
^XZ"""

# Zapisz do pliku desktop
simple_convert(zpl, r"C:\Users\tom\Desktop\test_zpl.pdf")
