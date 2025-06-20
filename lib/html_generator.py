#!/usr/bin/env python
# -*- coding: utf-8 -*-

import locale
from datetime import datetime


def format_currency(value):
    """Formatuje wartość walutową z separatorem tysięcy i przecinkiem."""
    if isinstance(value, str):
        try:
            value = float(value.replace(',', '.'))
        except ValueError:
            return "0,00"

    # Round to 2 decimal places
    value_rounded = round(value, 2)

    # Convert to string with comma as decimal separator
    value_str = f"{value_rounded:.2f}".replace('.', ',')

    # Add thousands separator (space)
    if value_rounded >= 1000:
        parts = value_str.split(',')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"

        # Add space as thousands separator
        integer_with_spaces = ""
        for i, char in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_with_spaces = " " + integer_with_spaces
            integer_with_spaces = char + integer_with_spaces

        value_str = f"{integer_with_spaces},{decimal_part}"

    return value_str


def generate_order_html(order_data, items, order_number=None, filter_product_type=None):
    """
    Generuje dokument HTML zamówienia z danych SQL.

    Args:
        order_data (dict): Słownik zawierający informacje o zamówieniu
        items (list): Lista słowników zawierających pozycje zamówienia
        contractor (dict, optional): Słownik zawierający informacje o kontraktorze
        order_number (str, optional): Niestandardowy numer zamówienia
        filter_product_type (str, optional): Filtr dla nazw produktów

    Returns:
        str: Dokument HTML jako string
    """
    # Upewnij się, że items jest listą (nie None)
    items = items or []

    # Ustawienie lokalizacji polskiej
    try:
        locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Polish_Poland.1250')
        except:
            pass

    # Data i czas
    order_date_time = datetime.now().strftime("%d.%m.%Y - %H:%M")

    uwagi = order_data.get('UWAGI', '')
    if not uwagi:
        uwagi = ''

    # Informacje o zamówieniu
    if not order_number:
        order_number = order_data.get('NUMER', '')
        if not order_number:
            order_number = f"ZO {datetime.now().strftime('%m%d')}/" + datetime.now().strftime('%y')

    # Dostęp do danych kontrahenta - dostosowanie do nowej struktury JSON
    kontrahent_data = order_data.get('kontrahent', {})

    # Tworzenie informacji o kontrahencie na podstawie nowej struktury
    contractor = {
        'name': kontrahent_data.get('NAZWA_PELNA', '') or order_data.get('KONTRAHENT_NAZWA', ''),
        'address': f"{kontrahent_data.get('KOD_POCZTOWY', '')} {kontrahent_data.get('MIEJSCOWOSC', '')}, ul.{kontrahent_data.get('ULICA_LOKAL', '')}",
        'nip': kontrahent_data.get('NIP', '') or '',
        'client_number': kontrahent_data.get('KOD_KONTRAHENTA', ''),
        'pesel': kontrahent_data.get('PESEL', '') or '',
        'order_number': order_data.get('NR_ZAMOWIENIA_KLIENTA', '')
    }

    # Przygotowanie pozycji - NIE filtrujemy ZREALIZOWANO > 0,
    # zamiast tego używamy wartości ZAMOWIONO dla ilości
    ordered_items = []
    for item in items:
        # Pobierz ilość ZAMOWIONO zamiast ZREALIZOWANO
        quantity_str = item.get('ZAMOWIONO', '0')
        if isinstance(quantity_str, str):
            quantity_str = quantity_str.replace(',', '.')

        try:
            quantity = float(quantity_str)
            # Pomiń pozycje z ilością 0
            if quantity <= 0:
                continue

            # Zastosuj filtr jeśli jest określony
            if filter_product_type:
                name = item.get('NAZWA_CALA', '') or item.get('NAZWA', '')
                if filter_product_type.lower() not in name.lower():
                    continue

            # Dodaj pozycję do listy
            ordered_items.append(item)
        except (ValueError, TypeError):
            # Jeśli konwersja nie powiedzie się, pomiń tę pozycję
            continue

    # Sortowanie pozycji po ID_ARTYKULU
    ordered_items = sorted(ordered_items, key=lambda item: int(item.get('ID_ARTYKULU', 0)))

    # Generowanie kodu kreskowego - teraz z nową strukturą
    # Najpierw sprawdzamy kod kreskowy zamówienia, potem kontrahenta
    KOD = order_data.get('KOD_KRESKOWY', '')
    # if not KOD:
    KOD2 = kontrahent_data.get('KOD_KRESKOWY', '')  # Sprawdź kod kreskowy kontrahenta

    if KOD is None:
        KOD = ""

    # Funkcja do formatowania walut
    def format_currency(value):
        """Formatuje wartość walutową z separatorem tysięcy i przecinkiem."""
        if isinstance(value, str):
            try:
                value = float(value.replace(',', '.'))
            except ValueError:
                return "0,00"

        # Round to 2 decimal places
        value_rounded = round(value, 2)

        # Convert to string with comma as decimal separator
        value_str = f"{value_rounded:.2f}".replace('.', ',')

        # Add thousands separator (space)
        if value_rounded >= 1000:
            parts = value_str.split(',')
            integer_part = parts[0]
            decimal_part = parts[1] if len(parts) > 1 else "00"

            # Add space as thousands separator
            integer_with_spaces = ""
            for i, char in enumerate(reversed(integer_part)):
                if i > 0 and i % 3 == 0:
                    integer_with_spaces = " " + integer_with_spaces
                integer_with_spaces = char + integer_with_spaces

            value_str = f"{integer_with_spaces},{decimal_part}"

        return value_str

    # Generowanie HTML
    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Zamówienie nr {order_number}</title>
  <style>
    body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 5mm;
            font-size: 14px;
        }}

        .center {{
            text-align: center;
        }}

        .right {{
            text-align: right;
        }}        
        .sum_left {{
            text-align: left;
            float: left;
            width: 40%;
        }}
        .sum_right {{
            text-align: right;
            float: right;
            width: 40%;
        }}
        .bold {{
            font-weight: bold;
        }}

        .order {{
            margin-bottom: 10px;
        }}
        .document {{
            display: inline;
        }}
        .header {{
            display: block;
            justify-content: space-between;
            float: right;
            /*margin-bottom: 10px;*/

        }}

        .title {{
            font-size: 16px;
            font-weight: bold;
            text-align: left;
            margin-top: 10px;
            margin-bottom: 10px;
        }}

        .date_time {{
            text-align: left;
        }}

        .client {{
            /*margin-bottom: 10px;*/
            display: block;
            float: left;
        }}

        .client-row {{
            margin-bottom: 3px;
        }}

        .client-label {{
            font-weight: bold;
        }}

        table {{
            border: 0px;
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            margin-bottom: 5px;
        }}

        .headtable {{
            font-weight: bold;
            width: 100%;
            border-collapse: collapse;
        }}

        .subheadtable {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            border: 1px solid #eeeeee;
            padding: 2px;
            text-align: left;
            word-wrap: break-word;
            overflow: hidden;
        }}

        .subheadtable td, .subheadtable th {{
            border: 0px solid #eeeeee;
            padding: 1px;
            text-align: right;
            font-weight: normal;
        }}

        .endtable {{
            width: 30%;
            text-align: right;
            float: right;
        }}

        th {{
            background-color: #eeeeee;
        }}

        .currency {{
            text-align: right;
        }}

        .barcode {{
            text-align: right;
            margin-bottom: 5px;
        }}

        .col-lp {{
            width: 7%;
        }}

        .col-name {{
            width: 93%;
            font-weight: bold;
        }}

        @media print {{
            body {{
                margin: 0;
                padding: 5mm;
            }}

            table {{
                width: 94%;
                font-size: 10px;
                border: 0px;
            }}

            .order {{
                page-break-after: avoid;
            }}
        }}
  </style>
  <script src="JsBarcode.all.min.js"></script>
</head>
<body>
  <div class="order">


    <div class="header">
      <div class="">      
      """

    if KOD and len(str(KOD)) > 7: html += f"""<barcode type="EAN13" data="{KOD}"></barcode>"""

    html += f"""
      </div>
      <div class="barcode">
      """

    if KOD and len(str(KOD)) > 7: html += f"""<svg id="barcode" data-barcode="{KOD}"></svg>"""

    html += f"""
      </div>
      <div class="date_time right">Data i godzina wydruku: {order_date_time}</div>
    </div>
    <div class="document">

        <div class="client">
            <div class="client-row">        
                <div class="title">Zamówienie nr {order_number}</div>
            </div>

              <div class="client-row">
                <div class="client-label">Zamawiający: </div>
                <div>{contractor['name']} (nr klienta {contractor['client_number']})</div>
              </div>
              <div class="client-row">
                <div class="client-label">Adres: </div>
                <div>{contractor['address']}</div>
              </div>
"""

    if contractor['nip'] and len(contractor['nip']) > 1: html += f"""
              <div class="client-row">
                <div class="client-label">NIP: </div>
                <div>{contractor['nip']}</div>
              </div>

"""

    if contractor['pesel'] and len(contractor['pesel']) > 1: html += f"""
      <div class="client-row">
        <div class="client-label">PESEL: </div>
        <div>{contractor['pesel']}</div>
      </div>
"""


    html += f"""
    
              <div class="client-row">
                <div class="client-label">Nr zam. klienta</div>
                <div>{contractor['order_number']}</div>
              </div>
        </div>
    </div>



    <table class="headtable">
      <thead>
        <tr>
          <th class="col-lp">Lp.</th>
          <th class="col-name">Nazwa towaru lub usługi</BR>
                <table class="subheadtable">          
                  <thead>
                        <tr>
                          <th>Ilość</th>
                          <th>Cena netto</th>
                          <th>Cena brutto</th>
                          <th>Rabat</th>
                          <th>Razem netto</th>
                          <th>Razem brutto</th>
                        </tr>
                    </thead>
                  <tbody>
               </table>
          </th>
        </tr>
      </thead>
      <tbody>
"""

    # Sprawdź czy lista pozycji jest pusta
    if not ordered_items:
        html += f"""
        <tr>
          <td colspan="2" class="empty-message">Brak pozycji w zamówieniu</td>
        </tr>
"""

    # Obliczanie sum
    total_netto = 0
    total_brutto = 0

    # Dodawanie pozycji do tabeli
    for i, item in enumerate(ordered_items, 1):
        name = item.get('NAZWA_CALA', '') or item.get('NAZWA', '')
        name += " - " + str(item.get('INDEKS_KATALOGOWY', ''))

        # Bezpieczna konwersja ilości - używamy ZAMOWIONO zamiast ZREALIZOWANO
        # quantity_str = item.get('DO_REZ_USER', '1')
        # if not quantity_str:
        quantity_str = item.get('ZAMOWIONO', '1')

        if isinstance(quantity_str, str):
            quantity_str = quantity_str.replace(',', '.')
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                continue  # Pomiń pozycje z ilością 0 lub mniejszą
        except (ValueError, TypeError):
            quantity = 1  # Domyślna wartość w przypadku błędu

        unit = item.get('JEDNOSTKA', 'szt.')

        # Parsowanie cen
        try:
            cena_netto_str = item.get('CENA_NETTO', '0')
            if isinstance(cena_netto_str, str):
                cena_netto_str = cena_netto_str.replace(',', '.')
            cena_netto = float(cena_netto_str)
        except (ValueError, TypeError):
            cena_netto = 0

        try:
            cena_brutto_str = item.get('CENA_BRUTTO', '0')
            if isinstance(cena_brutto_str, str):
                cena_brutto_str = cena_brutto_str.replace(',', '.')
            cena_brutto = float(cena_brutto_str)
        except (ValueError, TypeError):
            cena_brutto = 0

        # Pobieranie rabatu
        try:
            rabat_str = item.get('NARZUT', '0')
            if isinstance(rabat_str, str):
                rabat_str = rabat_str.replace(',', '.')
            rabat = float(rabat_str)
        except (ValueError, TypeError):
            rabat = 0

        # Obliczanie cen po rabacie
        cena_jedn_netto = cena_netto * (1 + rabat / 100)
        cena_jedn_brutto = cena_brutto * (1 + rabat / 100)

        # Obliczanie sum
        wartosc_netto = cena_jedn_netto * quantity
        wartosc_brutto = cena_jedn_brutto * quantity

        # Dodawanie do sum zamówienia
        total_netto += wartosc_netto
        total_brutto += wartosc_brutto

        # Dodawanie pozycji do tabeli
        html += f"""        <tr class="item-name">
                  <td class="col-lp">{i}</td>
                  <td class="col-name">{name}
                    <table class="subheadtable">
                      <tbody>
                        <tr>
                          <td>{int(quantity) if quantity.is_integer() else quantity} {unit}</td>
                          <td>{format_currency(cena_netto)}</td>
                          <td>{format_currency(cena_brutto)}</td>
                          <td>{format_currency(rabat)}</td>
                          <td>{format_currency(wartosc_netto)}</td>
                          <td>{format_currency(wartosc_brutto)}</td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
        """

    # Formatowanie sum
    total_netto_display = format_currency(total_netto)
    total_brutto_display = format_currency(total_brutto)

    # Dodawanie sum do tabeli
    html += f"""      </tbody>
            </table>

            <div style="display:inline">
                <div class="sum_left" >RAZEM:</div>
                <div class="sum_right">Wartość netto: <b>{total_netto_display}</b></div>
            </div>
            <br/>
            <div class="sum_right">Wartość brutto: <b>{total_brutto_display}</b></div>

        </div>
        <br/>
        <div class="left"><b>UWAGI: </b>{uwagi}</div>

  <script>
    // Generowanie kodu kreskowego
    JsBarcode("#barcode", "{KOD}", {{
      format: "CODE128",
      width: 1.7,
      height: 20,
      displayValue: true
    }});
  </script>
</body>
</html>"""

    return html
