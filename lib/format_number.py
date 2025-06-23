
def format_number(value):
    """Formatuje liczby zgodnie z formatem WAPRO"""
    if value is None:
        return "            0,00"
    return f"{value:>15,.2f}".replace(".", ",")
