# HTML2ZPL - Konwerter HTML do formatu ZPL

HTML2ZPL to narzędzie do konwersji dokumentów HTML (w tym faktur, zamówień i innych dokumentów z tabelami) do formatu ZPL (Zebra Programming Language) używanego przez drukarki etykiet Zebra.

## Możliwości

- Konwersja dokumentów HTML do formatu ZPL z zachowaniem układu
- Obsługa tabel, list, nagłówków i stylizacji tekstu
- Automatyczne dostosowanie układu do rozmiaru etykiety
- Wykrywanie drukarek Zebra w systemie
- Drukowanie na drukarkach Zebra (poprzez Win32 API lub komendy systemowe)
- Zapis kodu ZPL do pliku
- Tryb interaktywny

## Wymagania

- Python 3.6 lub nowszy
- BeautifulSoup4 (do parsowania HTML)
- PyWin32 (opcjonalnie, tylko na Windows)

## Instalacja


## Windows

1. Create and activate virtual environment:
2. 
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
python -m venv venv
venv\Scripts\activate
```

2. Install requirements:
   ```bash
   pip install --upgrade pip
   .\venv\Scripts\python.exe -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases


3. Start the server:
```bash
python zpl/html2zpl.py
```


## charset
https://labelary.com/viewer.html
The character set to use. Any number between 0 and 36 may be used. The default value is 0 (Code Page 850). 
It is recommended that you always use value 28 (UTF-8).
```
^XA
^CI28
...
```

## Użycie

Oto przykłady komend, które pozwolą Ci przetestować konwersję pliku HTML do formatu ZPL bez drukowania, zapisując wynik do pliku:

1. Podstawowa konwersja z domyślnym kodowaniem (cp852) i zapisem do pliku:
```
python zpl/html2zpl.py zamowienie.html --save
```

2. Konwersja z określonym kodowaniem (przykłady z różnymi kodowaniami):
```
python zpl/html2zpl.py zamowienie.html --save --encoding cp1250
python zpl/html2zpl.py zamowienie.html --save --encoding utf-8
python zpl/html2zpl.py zamowienie.html --save --encoding iso-8859-2
```

3. Konwersja z określeniem nazwy pliku wyjściowego:
```
python zpl/html2zpl.py zamowienie.html --save --output test_zpl_output.zpl
```

4. Konwersja z określonymi parametrami etykiety (szerokość, wysokość, rozdzielczość):
```
python zpl/html2zpl.py zamowienie.html --save --width 3.5 --height 6.0 --dpi 300
```

5. Kombinacja parametrów (kodowanie + własna nazwa pliku wyjściowego):
```
python zpl/html2zpl.py zamowienie.html --save --encoding utf-8 --output zamowienie_utf8.zpl
```

6. Konwersja z ustawieniami dla różnych formatów etykiet:
```
python zpl/html2zpl.py zamowienie.html --save --width 2.25 --height 4.0 --dpi 203
python zpl/html2zpl.py zamowienie.html --save --width 4.0 --height 6.0 --dpi 300
```

7. Tryb interaktywny z możliwością zapisania do pliku bez drukowania:
```
python zpl/html2zpl.py --interactive
```
(Następnie w interaktywnym interfejsie wybierz "t" przy pytaniu o zapis do pliku)


### Podstawowe użycie

```
python zpl/html2zpl.py zamowienie.html
```

```
python zpl/html2zpl.py dokument.html --printer "ZDesigner GK420d"
```

### Tryb interaktywny

```
python zpl/html2zpl.py -i
```

### Opcje wiersza poleceń

```
python zpl/html2zpl.py --help
```

Dostępne opcje:
- `--printer`, `-p` - Nazwa drukarki
- `--dpi` - Rozdzielczość drukarki w DPI (domyślnie: 203)
- `--width`, `-w` - Szerokość etykiety w calach (domyślnie: 4.0)
- `--height`, `-h` - Wysokość etykiety w calach (0 = auto, domyślnie: 0)
- `--encoding`, `-e` - Kodowanie znaków (domyślnie: cp852)
- `--save`, `-s` - Zapisz kod ZPL do pliku
- `--output`, `-o` - Ścieżka do pliku wyjściowego ZPL
- `--list`, `-l` - Wyświetl listę dostępnych drukarek
- `--interactive`, `-i` - Tryb interaktywny
- `--test`, `-t` - Wydrukuj etykietę testową

### Przykłady

1. Konwersja HTML do ZPL i zapis do pliku:
```
python zpl/html2zpl.py faktura.html -s -o faktura.zpl
```

2. Drukowanie na konkretnej drukarce z określonymi parametrami etykiety:
```
python zpl/html2zpl.py zamowienie.html -p "ZDesigner GK420d" --dpi 300 -w 4 -h 6
```

3. Wyświetlenie listy dostępnych drukarek:
```
python zpl/html2zpl.py -l
```

4. Wydrukowanie etykiety testowej:
```
python zpl/html2zpl.py -t -p "ZDesigner GK420d"
```

## Struktura projektu

Projekt jest podzielony na kilka plików:


```
html2zpl.py - Główny skrypt uruchamiany z wiersza poleceń z obsługą argumentów i trybem interaktywnym.
zpl_converter.py - Główna klasa konwertera HtmlToZpl, która zarządza całym procesem konwersji.
zpl_render_text.py - Funkcje do renderowania tekstu w ZPL.
zpl_render_table.py - Funkcje do renderowania tabel HTML jako tabel ZPL z zachowaniem formatowania.
zpl_parse_html.py - Funkcje do parsowania dokumentów HTML.
zpl_calculate_dimensions.py - Funkcje do obliczania wymiarów dokumentu.
zpl_text_utils.py - Narzędzia do przetwarzania tekstu.
zpl_encoding.py - Obsługa kodowania znaków.
zpl_utilities.py - Ogólne funkcje pomocnicze.
zpl_printer.py - Funkcje do drukowania na drukarkach Zebra.
zpl_utils.py - Funkcje do wykrywania drukarek i pracy z systemem operacyjnym.
zpl_html_processor.py - Funkcje do przetwarzania struktury HTML.
```

## Rozszerzenie funkcjonalności

Aby dodać obsługę nowych elementów HTML lub poprawić istniejącą, wystarczy zmodyfikować odpowiednie pliki:

- Dodanie nowego elementu HTML: zmodyfikuj plik `zpl_converter.py` i dodaj odpowiednią obsługę w metodzie `html_to_zpl`
- Poprawa renderowania tekstu: zmodyfikuj plik `zpl_render_text.py`
- Poprawa renderowania tabel: zmodyfikuj plik `zpl_render_table.py`


I've created a comprehensive ZPL to PDF converter script that will allow you to convert your Zebra Programming Language files to PDF format, which can then be printed on any standard printer.

## Features

- Converts ZPL files or raw ZPL strings to PDF
- Uses the Labelary API for accurate ZPL rendering
- Supports different DPI settings with the `--dpmm` parameter
- Option to automatically print the generated PDF
- Works on both Windows and Linux systems

## How to Use

1. **Install required packages**:
   ```
   pip install requests reportlab pillow
   ```
   For Windows printing support, also install:
   ```
   pip install pywin32
   ```

2. **Basic usage** - convert a ZPL file to PDF:
   ```
   python zpl_to_pdf.py my_label.zpl
   ```

3. **Convert and print** in one step:
   ```
   python zpl_to_pdf.py my_label.zpl --print
   ```

4. **Convert ZPL string directly**:
   ```
   python zpl_to_pdf.py "^XA^FO50,50^A0N,30,30^FDHello World^FS^XZ" --string -o output.pdf
   ```

5. **Specify custom output file**:
   ```
   python zpl_to_pdf.py my_label.zpl -o custom_name.pdf
   ```
    ```
   python zpl_to_pdf.py zpl/28.zpl -o pdf/28.pdf
   python zpl_to_pdf.py zpl/12.zpl -o pdf/12.pdf
   ```

## How It Works

1. The script reads your ZPL content (from a file or string)
2. It sends the ZPL to the Labelary API, which returns a PNG image
3. The image is then converted to a properly sized PDF document
4. If requested, the PDF can be automatically sent to your default printer

This solution is perfect for environments where you need to use ZPL but don't have a dedicated Zebra printer available.

Would you like me to explain any specific part of the code in more detail, or would you like help with using the converter in a specific scenario?


