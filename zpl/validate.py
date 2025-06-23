from zpl_file import *

# Walidacja pliku ZPL
result = validate_zpl_file("etykieta.zpl")
if not result['success']:
    for issue in result['issues']:
        if issue['type'] == 'error':
            print(f"BŁĄD: {issue['message']}")
        else:
            print(f"UWAGA: {issue['message']}")

# Naprawa pliku ZPL
repair_result = repair_zpl_file("etykieta.zpl")
if repair_result['success']:
    print(f"Status: {repair_result['message']}")
    if repair_result['fixed_issues']:
        print("Naprawione problemy:")
        for fix in repair_result['fixed_issues']:
            print(f"- {fix}")
