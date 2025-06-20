from datetime import datetime

def format_date(date_str):
    """Formatuje datę do czytelnej postaci"""
    try:
        if isinstance(date_str, str):
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        else:
            date = date_str
        return date.strftime('%d/%m/%Y')
    except:
        return date_str
