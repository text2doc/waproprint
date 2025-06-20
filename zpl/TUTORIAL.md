# HTML2ZPL - Instrukcja obsługi

Ten tutorial przeprowadzi Cię przez proces konwersji dokumentów HTML (w tym zamówień, faktur czy innych dokumentów) do formatu ZPL (Zebra Programming Language) używanego przez drukarki etykiet Zebra.

## Spis treści

1. [Instalacja](#1-instalacja)
2. [Podstawowa konwersja](#2-podstawowa-konwersja)
3. [Drukowanie](#3-drukowanie)
4. [Zastosowanie w środowisku biznesowym](#4-zastosowanie-w-środowisku-biznesowym)
5. [Częste problemy i rozwiązania](#5-częste-problemy-i-rozwiązania)

## 1. Instalacja

### Wymagania

- Python 3.6 lub nowszy
- BeautifulSoup4 (do parsowania HTML)
- PyWin32 (opcjonalnie, tylko na Windows)
- Drukarka Zebra (do drukowania, opcjonalnie)

### Kroki instalacji

1. Sklonuj lub pobierz repozytorium:
```
git clone https://github.com/twoj-uzytkownik/html2zpl.git
cd html2zpl
```

2. Zainstaluj wymagane zależności:
```
pip install -r requirements.txt
```

3. Sprawdź, czy instalacja przebiegła pomyślnie, wyświetlając listę dostępnych drukarek:
```
python html2zpl.py -l
```

## 2. Podstawowa konwersja

### Konwersja pliku HTML do ZPL

Aby przekonwertować dokument HTML do formatu ZPL:

```
python html2zpl.py dokument.html -s -o wyjscie.zpl
```

Opcje:
- `-s` - zapisuje wynik do pliku
- `-o wyjscie.zpl` - określa nazwę pliku wyjściowego

### Tryb interaktywny

Dla łatwiejszego użycia możesz wykorzystać tryb interaktywny:

```
python html2zpl.py -i
```

Program poprowadzi Cię przez proces krok po kroku, pytając o potrzebne parametry.

### Przykład konwersji przykładowego zamówienia

```
python example_order.py zamowienie.html
```

## 3. Drukowanie

### Bezpośrednie drukowanie na drukarce Zebra

```
python html2zpl.py dokument.html -p "ZDesigner GK420d"
```

Opcje:
- `-p "ZDesigner GK420d"` - określa nazwę drukarki

### Wydruk testowy

Aby szybko sprawdzić, czy drukarka działa poprawnie:

```
python html2zpl.py -t -p "ZDesigner GK420d"
```

Opcja `-t` generuje i drukuje testową etykietę.

### Ustawienia drukarki

Podstawowe parametry drukarki można określić za pomocą opcji:

```
python html2zpl.py dokument.html -p "ZDesigner GK420d" --dpi 300 -w 4 -h 6
```

Gdzie:
- `--dpi 300` - określa rozdzielczość drukarki (domyślnie 203)
- `-w 4` - szerokość etykiety w calach (domyślnie 4.0)
- `-h 6` - wysokość etykiety w calach (0 = automatyczne wykrywanie)

## 4. Zastosowanie w środowisku biznesowym

### Integracja z istniejącymi systemami

HTML2ZPL może być łatwo zintegrowany z istniejącymi systemami biznesowymi. Oto przykłady:

#### Drukowanie zamówień z systemu e-commerce

```python
from zpl_converter import HtmlToZpl
from network_printer import print_raw_zpl

def drukuj_zamowienie(numer_zamowienia, html_zamowienia, drukarka="ZDesigner GK420d"):
    # Utwórz konwerter
    converter = HtmlToZpl(
        printer_name=drukarka,
        dpi=203,
        label_width=4.0
    )
    
    # Konwertuj HTML do ZPL
    zpl_code = converter.html_to_zpl(html_zamowienia)
    
    # Drukuj na drukarce
    print_raw_zpl(zpl_code, drukarka)
    
    return True
```

#### Automatyzacja z crontab lub Windows Task Scheduler

Możesz skonfigurować skrypt tak, aby automatycznie przetwarzał i drukował dokumenty z określonego folderu:

```python
import os
import time
from zpl_converter import HtmlToZpl
from network_printer import print_raw_zpl

def monitoruj_folder_i_drukuj(folder_path, drukarka):
    while True:
        for file in os.listdir(folder_path):
            if file.endswith('.html'):
                file_path = os.path.join(folder_path, file)
                print(f"Przetwarzanie: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                converter = HtmlToZpl(printer_name=drukarka)
                zpl_code = converter.html_to_zpl(html_content)
                print_raw_zpl(zpl_code, drukarka)
                
                # Przenieś przetworzone pliki do folderu 'done'
                os.rename(file_path, os.path.join(folder_path, 'done', file))
        
        # Oczekiwanie przed kolejnym sprawdzeniem folderu
        time.sleep(60)
```

### Dostosowanie dla różnych formatów dokumentów

Skrypt jest elastyczny i może być dostosowany do różnych formatów dokumentów w Twojej firmie:

1. **Faktury** - najlepiej działa z tabelarycznym układem danych
2. **Listy przewozowe** - możliwość drukowania kodów kreskowych
3. **Etykiety wysyłkowe** - obsługa adresów i informacji logistycznych
4. **Metryki produktów** - informacje o produktach, np. na półki sklepowe

## 5. Częste problemy i rozwiązania

### Problem: Niepoprawne polskie znaki na wydruku

**Rozwiązanie**: Upewnij się, że używasz właściwego kodowania:

```
python html2zpl.py dokument.html -e cp1250
```

### Problem: Tabela jest ucięta na wydruku

**Rozwiązanie**: Skrypt automatycznie dostosowuje szerokość kolumn, ale możesz zwiększyć szerokość etykiety:

```
python html2zpl.py dokument.html -w 6
```

### Problem: Drukarki nie są wykrywane

**Rozwiązanie**: 
1. Sprawdź, czy drukarka jest włączona i podłączona
2. Upewnij się, że sterowniki drukarki są prawidłowo zainstalowane
3. Na Windows może być potrzebne uruchomienie z uprawnieniami administratora

### Problem: Błędy kodowania ZPL

**Rozwiązanie**:
1. Zapisz kod ZPL do pliku i sprawdź jego zawartość:
```
python html2zpl.py dokument.html -s -o debug.zpl
```
2. Sprawdź, czy w dokumencie HTML nie ma elementów nieobsługiwanych przez ZPL (np. złożonych obrazów)

### Problem: Wydruk jest zbyt wolny

**Rozwiązanie**: Zoptymalizuj kod ZPL poprzez zmniejszenie rozmiaru czcionki dla mniej ważnych elementów:

```
python html2zpl.py dokument.html --dpi 203
```