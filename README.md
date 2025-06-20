# waproprint


# WaproPrintSystem - System automatycznego drukowania dokumentów ZO z Wapro Mag

## Opis

Prosty system monitorujący bazę danych Wapro Mag i automatycznie drukujący dokumenty Zamówień Odbiorcy (ZO) na drukarce termicznej. System działa jako usługa Windows, sprawdzając co 5 sekund (konfigurowalne) bazę danych w poszukiwaniu nowych dokumentów ZO i drukując je w formie PDF na wskazanej drukarce.

Drukarka: 8.169
PC:  8.20

## Wymagania

- Windows 10/11
- Python 3.7 lub nowszy
- Sterownik ODBC dla SQL Server
- https://wapro.pl/dokumentacja-erp/desktop/docs/instalacja-programu/reczna-instalacja-serwera-baz/mg-instalacja-krok-po-kroku/
- https://www.microsoft.com/en-us/download/details.aspx?id=101064
- 
- Drukarka termiczna (np. ZD421) skonfigurowana w systemie
- Dostęp do bazy danych Wapro Mag

## Instalacja

### ghostpdl 10.05.0

https://github.com/ArtifexSoftware/ghostpdl-downloads/releases

### 1. Instalacja Pythona

1. Pobierz i zainstaluj Python 3.7 lub nowszy ze strony [python.org](https://www.python.org/downloads/)
2. Podczas instalacji zaznacz opcję "Add Python to PATH"

### 2. Instalacja wymaganych bibliotek

Uruchom wiersz poleceń jako administrator i wykonaj:

```
pip install pywin32 pyodbc reportlab configparser
```

### 3. Instalacja sterownika ODBC dla SQL Server

Jeśli nie masz zainstalowanego sterownika ODBC dla SQL Server:

1. Pobierz sterownik ze strony Microsoftu: [Microsoft ODBC Driver for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. Zainstaluj sterownik zgodnie z instrukcjami

### 4. Przygotowanie plików systemu

1. Umieść wszystkie pliki projektu w wybranym katalogu, np. `C:\WaproPrintSystem`
2. Dostosuj plik konfiguracyjny `config.ini` do swoich potrzeb:
   - Ustaw parametry połączenia z bazą danych
   - Skonfiguruj nazwę drukarki
   - Ustaw folder tymczasowy
   - Określ dozwolonych użytkowników (opcjonalnie)

### 5. Instalacja i uruchomienie usługi

1. Uruchom wiersz poleceń jako administrator
2. Przejdź do katalogu z plikami systemu: `cd C:\WaproPrintSystem`
3. Uruchom skrypt instalacyjny: `install.bat`
4. Wybierz opcję "1" aby zainstalować usługę
5. Wybierz opcję "2" aby uruchomić usługę

## Konfiguracja

Plik `config.ini` zawiera wszystkie ustawienia systemu:

### Sekcja [DATABASE]

```ini
[DATABASE]
server = localhost
database = WAPRO
trusted_connection = yes
# lub dla uwierzytelniania SQL:
# trusted_connection = no
# username = sa
# password = StrongPassword123
```

- `server` - nazwa serwera SQL
- `database` - nazwa bazy danych Wapro
- `trusted_connection` - czy używać uwierzytelniania Windows
- `username` i `password` - dane logowania dla uwierzytelniania SQL

### Sekcja [PRINTING]

```ini
[PRINTING]
printer_name = ZD421
temp_folder = C:\WaproPrints
check_interval = 5
```

- `printer_name` - dokładna nazwa drukarki w systemie Windows
- `temp_folder` - katalog do przechowywania tymczasowych plików PDF
- `check_interval` - częstotliwość sprawdzania bazy danych (w sekundach)

### Sekcja [USERS]

```ini
[USERS]
allowed_users = admin,operator
```

- `allowed_users` - lista dozwolonych użytkowników (operatorów) oddzielonych przecinkami

### Sekcja [DOCUMENT]

```ini
[DOCUMENT]
paper_width = 80
print_logo = no
# logo_path = C:\WaproPrints\logo.png
```

- `paper_width` - szerokość papieru w mm
- `print_logo` - czy drukować logo firmy
- `logo_path` - ścieżka do pliku z logo (opcjonalna)

## Użytkowanie

Po zainstalowaniu i uruchomieniu usługi, system działa automatycznie:

1. Monitoruje bazę danych Wapro Mag co 5 sekund (lub zgodnie z konfiguracją)
2. Wykrywa nowe dokumenty ZO utworzone przez dozwolonych użytkowników
3. Generuje pliki PDF z dokumentami
4. Drukuje dokumenty na wskazanej drukarce termicznej
5. Zapisuje informacje o wydrukach w tabeli `WaproPrintHistory` w bazie danych
6. Prowadzi dziennik zdarzeń w plikach `db_monitor.log` i `service_wrapper.log`





python install_service.py




Widzę, że występuje problem z uruchamianiem usługi. Spróbujmy naprawić to używając ulepszonej wersji usługi (`enhanced_service.py`), która ma lepszą obsługę błędów i diagnostykę.

Najpierw zatrzymajmy i usuńmy obecną usługę:

```powershell
python db_monitor.py stop
python db_monitor.py remove
```

Teraz zainstalujmy ulepszoną wersję usługi:

```powershell
python enhanced_service.py install
```

I uruchommy ją:

```powershell
python enhanced_service.py start
```

Główne zmiany w ulepszonej wersji usługi:
1. Lepsza obsługa błędów i logowanie
2. Bezpieczniejsze uruchamianie procesów
3. Poprawna obsługa ścieżek i katalogów
4. Lepsze zarządzanie zmiennymi środowiskowymi
5. Bardziej szczegółowa diagnostyka

Jeśli usługa nadal nie działa, sprawdźmy logi:

```powershell
python enhanced_service.py status
```

Dodatkowo, możemy spróbować uruchomić usługę w trybie debug, aby zobaczyć dokładnie, co się dzieje:

```powershell
python enhanced_service.py debug
```

Jeśli nadal występują problemy, proszę o przesłanie zawartości pliku `enhanced_service.log` po wykonaniu tych kroków. Szczególnie interesują mnie komunikaty błędów, które mogą wskazywać na przyczynę problemu.

Dodatkowo, sprawdźmy czy plik `sql2html.py` ma odpowiednie uprawnienia i czy wszystkie zależności są poprawnie zainstalowane:

```powershell
python sql2html.py
```

To pomoże nam zidentyfikować, czy problem leży w samej usłudze, czy w skrypcie `sql2html.py`.


# Instrukcja naprawy i konfiguracji usługi monitorowania SQL

## Diagnoza problemu

Na podstawie przesłanych logów zidentyfikowano następujące problemy:

1. **Problem z usługą Windows**: Usługa działa prawidłowo w trybie debug, ale nie działa po zainicjowaniu jako usługa Windows
2. **Problem z katalogiem roboczym**: Usługa może mieć problem z ustawieniem właściwego katalogu roboczego
3. **Problem z uprawnieniami**: Usługa działająca jako Windows Service może nie mieć odpowiednich uprawnień
4. **Problem z kodowaniem**: Widoczne problemy z polskimi znakami w logach

## Rozwiązanie

Przygotowałem trzy skrypty, które rozwiązują wszystkie powyższe problemy:

1. `enhanced_service.py` - ulepszona usługa Windows z poprawioną obsługą:
   - katalogów roboczych
   - uprawnień
   - kodowania znaków
   - logowania

2. `install_service.py` - narzędzie do instalacji/zarządzania usługą:
   - instalacja/deinstalacja usługi
   - zatrzymywanie/uruchamianie usługi
   - pełna reinstalacja usługi

3. `manual_run.py` - skrypt do ręcznego uruchomienia monitorowania w trybie interaktywnym:
   - uruchamia sql2html.py co 5 sekund
   - monitoruje wyjście w czasie rzeczywistym
   - nie wymaga instalacji usługi

## Instrukcja wdrożenia

Wykonaj poniższe kroki, aby naprawić usługę:

### 1. Utwórz nowe pliki

Utwórz trzy nowe pliki w katalogu `C:\Users\tom\github\zlecenia\wapromagpy\`:

- `enhanced_service.py` - zawartość z pierwszego artefaktu
- `install_service.py` - zawartość z drugiego artefaktu
- `manual_run.py` - zawartość z trzeciego artefaktu

### 2. Testowanie w trybie ręcznym

Przed instalacją usługi, zaleca się przetestowanie działania w trybie ręcznym:

```powershell
python install_service.py
```

Wybierz opcję 6 (Pełna reinstalacja), która:
- Zatrzyma i usunie starą usługę (jeśli istnieje)
- Zainstaluje nową usługę
- Uruchomi nową usługę

### 5. Weryfikacja działania

Nowa usługa powinna być widoczna w Usługach Windows jako "Enhanced DB Monitor Service".
Sprawdź logi w pliku `enhanced_service.log` aby upewnić się, że usługa działa poprawnie.


# Uruchamianie skryptu co 5 sekund w Windows Server

W Windows Server możesz skonfigurować uruchamianie skryptu co 5 sekund na kilka sposobów. Oto najlepsze rozwiązania:

## Opcja 1: Skrypt pętli w tle

Najłatwiejszym rozwiązaniem jest stworzenie skryptu, który sam się uruchamia w pętli co 5 sekund i działa w tle:

1. **Użyj skryptu `db_monitor_nonservice.py`, który już posiadasz**:
   - Ten skrypt zawiera wewnętrzną pętlę, która uruchamia `sql2html.py` co 5 sekund
   - Można go uruchomić jako zwykły proces: `python db_monitor_nonservice.py`

2. **Uruchamianie przy starcie systemu**:
   - Utwórz plik .bat w katalogu autostartu lub skonfiguruj zadanie w harmonogramie, które uruchomi się przy starcie systemu

## Opcja 2: Konfiguracja zadania w harmonogramie zadań (Task Scheduler)

Jeśli chcesz użyć harmonogramu zadań Windows, skonfiguruj go do uruchamiania co 5 sekund:

1. **Otwórz Harmonogram zadań**:
   - W menu Start wpisz `taskschd.msc` lub przejdź do Panelu sterowania → Narzędzia administracyjne → Harmonogram zadań

2. **Utwórz nowe zadanie**:
   - Kliknij prawym przyciskiem na "Biblioteka harmonogramu zadań" i wybierz "Utwórz zadanie"
   - Na zakładce "Ogólne":
     * Nadaj nazwę, np. "DB Monitor SQL"
     * Wybierz "Uruchom niezależnie od tego, czy użytkownik jest zalogowany"
     * Zaznacz "Uruchom z najwyższymi uprawnieniami"

3. **Ustaw wyzwalacz**:
   - Przejdź do zakładki "Wyzwalacze"
   - Kliknij "Nowy..." i wybierz "Przy uruchomieniu"
   - W sekcji "Ustawienia zaawansowane":
     * Zaznacz "Powtórz zadanie co:" i wpisz "5 sekund" 
     * W polu "przez:" wybierz "nieokreślony"
   - Kliknij OK

4. **Skonfiguruj akcję**:
   - Przejdź do zakładki "Akcje"
   - Kliknij "Nowy..."
   - Akcja: "Uruchom program"
   - Program/skrypt: `python`
   - Dodaj argumenty: `C:\Users\[USERNAME]\wapromag\sql2html.py`
   - Rozpocznij w: `C:\Users\[USERNAME]\wapromag`
   - Kliknij OK

5. **Ustaw dodatkowe opcje**:
   - W zakładce "Ustawienia" zaznacz:
     * "Zezwalaj na uruchamianie zadania na żądanie"
     * "Uruchom zadanie tak szybko, jak to możliwe po niewykonanym zaplanowanym uruchomieniu"
     * W "Jeśli zadanie już działa, obowiązuje następująca reguła:" wybierz "Zatrzymaj istniejące wystąpienie"

6. **Zapisz i przetestuj**:
   - Kliknij OK, aby zapisać zadanie
   - Znajdź zadanie na liście, kliknij prawym przyciskiem i wybierz "Uruchom"
   - Sprawdź dzienniki, aby potwierdzić, że zadanie działa prawidłowo

## Opcja 3: Skrypt wsadowy z pętlą

Możesz utworzyć prosty skrypt .bat z pętlą nieskończoną:

```batch
@echo off
:loop
    echo Uruchamianie sql2html.py...
    python C:\Users\[USERNAME]\wapromag\sql2html.py
    timeout /t 5 /nobreak
goto loop
```

Zapisz ten skrypt jako `run_monitor.bat` i skonfiguruj jego uruchamianie przy starcie systemu.

## Zalecane rozwiązanie

Dla serwera produkcyjnego najbardziej zalecane jest rozwiązanie z opcji 1 - używanie skryptu `db_monitor_nonservice.py`, który sam zawiera logikę pętli i jest bardziej odporny na błędy. Następnie skonfiguruj jedno zadanie w harmonogramie zadań, które uruchamia ten skrypt przy starcie systemu.






## Rozwiązywanie problemów

Jeśli nadal występują problemy:

1. Sprawdź logi w plikach:
   - `enhanced_service.log` - logi nowej usługi
   - `service_install.log` - logi instalacji usługi
   - `manual_run.log` - logi z ręcznego uruchomienia

2. Upewnij się, że ścieżki w skryptach są prawidłowe:
   - `SCRIPT_DIR` powinien wskazywać na katalog z plikami skryptów
   - `sql2html_path` powinien wskazywać na plik sql2html.py

3. Sprawdź uprawnienia:
   - Usługa domyślnie działa jako LocalSystem
   - Upewnij się, że użytkownik ma dostęp do bazy danych
   - Jeśli potrzebne są szczególne uprawnienia, zmodyfikuj konto usługi w ustawieniach Windows

4. Problem z kodowaniem:
   - Skrypty ustawiają kodowanie utf-8 i obsługują polskie znaki
   - W przypadku problemów z kodowaniem, sprawdź ustawienia systemowe Windows

## Uruchamianie po restarcie komputera

Usługa jest skonfigurowana do automatycznego uruchamiania po restarcie komputera. Jeśli to nie działa:

1. Otwórz Panel sterowania → Narzędzia administracyjne → Usługi
2. Znajdź "Enhanced DB Monitor Service"
3. Kliknij prawym przyciskiem myszy i wybierz "Właściwości"
4. Ustaw typ uruchamiania na "Automatyczny"
5. Kliknij "OK"

## Dodatkowe informacje

Jeśli pojawi się konieczność zmiany konfiguracji nowej usługi, należy:

1. Zmodyfikować plik `enhanced_service.py`
2. Uruchomić skrypt `install_service.py` i wybrać opcję 6 (pełna reinstalacja)

W razie potrzeby testowania bez usługi, zawsze można użyć skryptu `manual_run.py`.

## Podsumowanie zmian

Nowe rozwiązanie naprawia problemy z:
- Uruchamianiem usługi Windows
- Katalogiem roboczym
- Uprawnieniami
- Kodowaniem polskich znaków
- Zarządzaniem usługą

Dzięki tym zmianom, usługa powinna działać stabilnie w środowisku produkcyjnym.

python manual_run.py
```

Ten tryb pozwala weryfikować działanie skryptu sql2html.py bez instalowania usługi.
Naciśnij Ctrl+C, aby zatrzymać program.

### 3. Zatrzymaj i usuń starą usługę

Jeśli stara usługa jest już zainstalowana, należy ją zatrzymać i usunąć:

```powershell
sc stop DBMonitorService
sc delete DBMonitorService
```

### 4. Instalacja i uruchomienie nowej usługi

Uruchom skrypt instalacyjny z uprawnieniami administratora:








python enhanced_service_fixed.py debug







# Uruchamianie skryptu co 5 sekund w Windows Server

W Windows Server możesz skonfigurować uruchamianie skryptu co 5 sekund na kilka sposobów. Oto najlepsze rozwiązania:

## Opcja 1: Skrypt pętli w tle

Najłatwiejszym rozwiązaniem jest stworzenie skryptu, który sam się uruchamia w pętli co 5 sekund i działa w tle:

1. **Użyj skryptu `db_monitor_nonservice.py`, który już posiadasz**:
   - Ten skrypt zawiera wewnętrzną pętlę, która uruchamia `sql2html.py` co 5 sekund
   - Można go uruchomić jako zwykły proces: `python db_monitor_nonservice.py`

2. **Uruchamianie przy starcie systemu**:
   - Utwórz plik .bat w katalogu autostartu lub skonfiguruj zadanie w harmonogramie, które uruchomi się przy starcie systemu

## Opcja 2: Konfiguracja zadania w harmonogramie zadań (Task Scheduler)

Jeśli chcesz użyć harmonogramu zadań Windows, skonfiguruj go do uruchamiania co 5 sekund:

1. **Otwórz Harmonogram zadań**:
   - W menu Start wpisz `taskschd.msc` lub przejdź do Panelu sterowania → Narzędzia administracyjne → Harmonogram zadań

2. **Utwórz nowe zadanie**:
   - Kliknij prawym przyciskiem na "Biblioteka harmonogramu zadań" i wybierz "Utwórz zadanie"
   - Na zakładce "Ogólne":
     * Nadaj nazwę, np. "DB Monitor SQL"
     * Wybierz "Uruchom niezależnie od tego, czy użytkownik jest zalogowany"
     * Zaznacz "Uruchom z najwyższymi uprawnieniami"

3. **Ustaw wyzwalacz**:
   - Przejdź do zakładki "Wyzwalacze"
   - Kliknij "Nowy..." i wybierz "Przy uruchomieniu"
   - W sekcji "Ustawienia zaawansowane":
     * Zaznacz "Powtórz zadanie co:" i wpisz "5 sekund" 
     * W polu "przez:" wybierz "nieokreślony"
   - Kliknij OK

4. **Skonfiguruj akcję**:
   - Przejdź do zakładki "Akcje"
   - Kliknij "Nowy..."
   - Akcja: "Uruchom program"
   - Program/skrypt: `python`
   - Dodaj argumenty: `C:\Users\[USERNAME]\wapromag\sql2html.py`
   - Rozpocznij w: `C:\Users\[USERNAME]\wapromag`
   - Kliknij OK

5. **Ustaw dodatkowe opcje**:
   - W zakładce "Ustawienia" zaznacz:
     * "Zezwalaj na uruchamianie zadania na żądanie"
     * "Uruchom zadanie tak szybko, jak to możliwe po niewykonanym zaplanowanym uruchomieniu"
     * W "Jeśli zadanie już działa, obowiązuje następująca reguła:" wybierz "Zatrzymaj istniejące wystąpienie"

6. **Zapisz i przetestuj**:
   - Kliknij OK, aby zapisać zadanie
   - Znajdź zadanie na liście, kliknij prawym przyciskiem i wybierz "Uruchom"
   - Sprawdź dzienniki, aby potwierdzić, że zadanie działa prawidłowo

## Opcja 3: Skrypt wsadowy z pętlą

Możesz utworzyć prosty skrypt .bat z pętlą nieskończoną:

```batch
@echo off
:loop
    echo Uruchamianie sql2html.py...
    python C:\Users\[USERNAME]\wapromag\sql2html.py
    timeout /t 5 /nobreak
goto loop
```

Zapisz ten skrypt jako `run_monitor.bat` i skonfiguruj jego uruchamianie przy starcie systemu.

## Zalecane rozwiązanie

Dla serwera produkcyjnego najbardziej zalecane jest rozwiązanie z opcji 1 - używanie skryptu `db_monitor_nonservice.py`, który sam zawiera logikę pętli i jest bardziej odporny na błędy. Następnie skonfiguruj jedno zadanie w harmonogramie zadań, które uruchamia ten skrypt przy starcie systemu.




















## install 

```
pip install -r requirements.txt
```

```
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

```
python db_monitor.py install
python db_monitor.py start
python db_monitor.py stop
python db_monitor.py status
python db_monitor.py remove
```        


```
# a manual registry cleanup:
reg delete "HKLM\SYSTEM\CurrentControlSet\Services\DBMonitorService" /f

# check the details of the service installation:
sc qc DBMonitorService
sc queryex DBMonitorService

# Przejdź do katalogu ze skryptem
cd C:\Users\tom\github\zlecenia\wapromagpy

# Zainstaluj usługę z pełną ścieżką do Pythona
python db_monitor.py install --startup=auto

# Uruchom usługę
python db_monitor.py start

python -m pip install --upgrade pywin32
python pywin32_postinstall.py -install

```









1. Open an administrative PowerShell
2. Run these commands:
```powershell
# Stop the service if it's running
sc stop DBMonitorService

# Delete the service
sc delete DBMonitorService

# Clean up registry entries
reg delete "HKLM\SYSTEM\CurrentControlSet\Services\DBMonitorService" /f
```

If those commands don't work, we'll need to diagnose further. Let's create a more comprehensive diagnostic script:

I recommend taking these steps:

1. Save the script as `service_diagnostic.py`
2. Run it with administrative privileges:
```powershell
python service_diagnostic.py
```
3. Share the contents of `service_diagnostic.log`

Additionally, please run these commands in an administrative PowerShell and share the outputs:
```powershell
wmic service where name="DBMonitorService" get *
```

This will help us understand:
- The exact state of the service
- Any registry entries
- Potential permission or configuration issues






Let's diagnose this further. The error code 1058 suggests there might be an issue with the service configuration. 

I'll create a comprehensive diagnostic script that will help us understand exactly what's happening:

I'll also create a more robust installation script:

Recommended steps:

1. Run the diagnostic script to gather more information:
```powershell
python advanced_service_diagnostics.py
```

2. Then run the ultimate installation script:
```powershell
python ultimate_service_installation.py
```

Please share:
1. Contents of `service_deep_diagnostics.log`
2. Contents of `ultimate_service_installation.log`
3. Output of these commands in an admin PowerShell:
```powershell
sc qc DBMonitorService
reg query "HKLM\SYSTEM\CurrentControlSet\Services\DBMonitorService"
```

Some potential issues that could cause error 1058:
- Incorrect service binary path
- Missing dependencies
- Permissions issues
- Corrupt service configuration






This is a persistent Windows service configuration issue. Let's try a more manual approach:

1. First, we'll create a PowerShell script to forcefully clean up the service:

2. Save this script as `clean_service.ps1`

3. Open an administrative PowerShell and run:
```powershell
powershell.exe -ExecutionPolicy Bypass -File clean_service.ps1
```

Then try installing the service:
```powershell
python db_monitor.py install
```

If this doesn't work, we'll need to do a more in-depth investigation. 

The "marked for deletion" error typically occurs when:
1. A previous service removal was interrupted
2. There are lingering references in the Windows service configuration
3. There are permission issues preventing complete service removal

To help diagnose, could you also run these commands in an admin PowerShell and share the output:
```powershell
# Check service details
sc.exe qc DBMonitorService

# List all services containing DBMonitor
Get-Service | Where-Object { $_.Name -like "*DBMonitor*" }

# Check registry entries
Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Services" | 
    Where-Object { $_.Name -like "*DBMonitorService*" } | 
    Select-Object Name
```

Would you like to proceed with these steps?





The service still appears to be in a problematic state. Let's try a more aggressive approach:

1. First, I'll create a Python script that uses advanced Windows API techniques to force service removal:

2. Save the script as `advanced_service_cleanup.py`

3. Run the script with administrative privileges:
```powershell
python advanced_service_cleanup.py
```

4. Then try installing the service:
```powershell
python db_monitor.py install
```

This script provides a more comprehensive approach to service removal:
- Multiple removal methods
- Detailed logging
- Attempts to stop and remove the service through various Windows APIs
- Handles registry cleanup

Would you like to proceed with these steps? If successful, this should clear out any lingering service configuration and allow you to reinstall the service.

Please share:
1. The output of the `advanced_service_cleanup.py` script
2. The contents of `advanced_service_cleanup.log`
3. Any errors when trying to install the service






This persistent issue suggests a deep-seated problem with the Windows Service configuration. Let's try a more extreme approach:

1. First, use Windows Management Instrumentation (WMI) to forcefully remove the service:

Open an administrative PowerShell and run:
```powershell
# Use WMI to find and remove the service
$service = Get-WmiObject -Class Win32_Service | Where-Object {$_.Name -eq "DBMonitorService"}
if ($service) {
    $service.Delete()
}

# Additional cleanup
sc.exe delete DBMonitorService /f
reg delete "HKLM\SYSTEM\CurrentControlSet\Services\DBMonitorService" /f
```

2. I'll create a comprehensive WMI-based removal script:

IMPORTANT: Before running this script, you'll need to install the `wmi` package:
```powershell
pip install wmi
```

3. Save the script as `extreme_service_removal.py`

4. Run the script with administrative privileges:
```powershell
python extreme_service_removal.py
```

5. Then attempt to install the service:
```powershell
python db_monitor.py install
```

This script uses multiple removal methods:
- Windows Management Instrumentation (WMI)
- Service Control (SC)
- PyWin32
- Registry entry removal
- Verification of removal

Please share:
1. The output of the `extreme_service_removal.py` script
2. The contents of `extreme_service_removal.log`
3. Any errors when trying to install the service






The error message indicates that the service "DBMonitorService" already exists in the Windows Service Manager. Here are the steps to resolve this:

1. First, remove the existing service:
```powershell
sc delete DBMonitorService
```

2. Then, try reinstalling the service:
```powershell
python db_monitor.py install
```


## Usługa Windows

1. Save the script as `service_management.py` in the same directory as your service files.

2. Remove the existing service:
```powershell
python service_management.py remove
```

3. Install the service:
```powershell
python service_management.py install
```

4. If you want to completely remove and reinstall:
```powershell
python service_management.py reinstall
```

The script provides:
- Detailed logging to `service_management.log`
- Error handling
- Environment diagnostics
- Ability to remove, install, or reinstall the service

## Rozwiązywanie problemów

Przepraszam za zamieszanie. Spróbujmy najpierw sprawdzić status usługi, a następnie zatrzymać ją w bezpieczny sposób:

1. Najpierw sprawdź status usługi:
```powershell
python db_monitor.py status
```

2. Następnie spróbuj zatrzymać usługę:
```powershell
python db_monitor.py stop
```

3. Jeśli usługa nadal działa, spróbujmy odinstalować ją:
```powershell
python db_monitor.py remove
```

4. Następnie zainstalujmy usługę ponownie:
```powershell
python db_monitor.py install
```

5. I uruchommy ją:
```powershell
python db_monitor.py start
```

5. I uruchommy ją:
```powershell
python db_monitor.py test
```

Jeśli powyższe kroki nie pomogą, możemy spróbować zatrzymać usługę przez Windows Services:

1. Naciśnij `Win + R`
2. Wpisz `services.msc` i naciśnij Enter
3. Znajdź usługę "DB Monitor Service"
4. Kliknij prawym przyciskiem myszy i wybierz "Stop"
5. Następnie spróbuj ponownie uruchomić usługę przez komendę:
```powershell
python db_monitor.py start
```

Daj znać, czy któreś z tych rozwiązań pomogło. Jeśli nie, możemy spróbować innych metod.


### Sprawdzanie logów

W przypadku problemów sprawdź pliki logów:
- `db_monitor.log` - główny log działania systemu
- `service_wrapper.log` - log usługi Windows
- `stdout.log` i `stderr.log` - standardowe wyjście i błędy skryptu

### Uruchamianie w trybie konsoli

Aby uruchomić system w trybie konsoli (do diagnozowania problemów):
1. Uruchom `install.bat`
2. Wybierz opcję "5. Uruchom w trybie konsoli"

### Typowe problemy

- **Problem z połączeniem do bazy danych**: Sprawdź ustawienia w sekcji [DATABASE]
- **Drukarka nie drukuje**: Upewnij się, że nazwa drukarki w konfiguracji jest dokładnie taka sama jak w systemie Windows
- **Usługa nie uruchamia się**: Sprawdź logi i upewnij się, że masz uprawnienia administratora
- **Dokumenty nie są wykrywane**: Sprawdź, czy dokumenty są typu ZO i czy utworzyli je dozwoleni użytkownicy

# Dokumentacja WaproPrintSystem - Lista plików

Poniżej przedstawiam kompletną listę plików składających się na system automatycznego drukowania dokumentów ZO z bazy danych Wapro Mag.

## Pliki główne

1. **db_monitor.py** ✅
   - Główny skrypt monitorujący bazę danych i drukujący dokumenty
   - Status: **Utworzony**

2. **service_wrapper.py** ✅
   - Wrapper umożliwiający uruchomienie skryptu jako usługa Windows
   - Status: **Utworzony**

3. **config.ini** ✅
   - Plik konfiguracyjny zawierający ustawienia systemu
   - Status: **Utworzony**

4. **install.bat** ✅
   - Skrypt instalacyjny do konfiguracji, instalacji i zarządzania usługą
   - Status: **Utworzony**

5. **README.md** ✅
   - Dokumentacja systemu z instrukcjami instalacji i użytkowania
   - Status: **Utworzony**

## Pliki generowane automatycznie podczas pracy systemu

6. **db_monitor.log**
   - Plik logów z działania głównego skryptu
   - Status: Generowany automatycznie podczas pracy skryptu

7. **service_wrapper.log**
   - Plik logów z działania usługi Windows
   - Status: Generowany automatycznie podczas pracy usługi

8. **stdout.log** i **stderr.log**
   - Pliki zawierające standardowe wyjście i błędy skryptu
   - Status: Generowane automatycznie podczas pracy usługi

## Pliki tymczasowe

9. **Pliki PDF w folderze tymczasowym**
   - Tymczasowe pliki PDF generowane przed drukowaniem
   - Status: Generowane podczas pracy systemu, usuwane po wydrukowaniu

## Baza danych

10. **Tabela WaproPrintHistory**
    - Tabela w bazie danych Wapro Mag do śledzenia wydrukowanych dokumentów
    - Status: Tworzona automatycznie podczas pierwszego uruchomienia skryptu

## Podsumowanie

Wszystkie niezbędne pliki do działania systemu zostały utworzone. System jest kompletny i gotowy do wdrożenia.

Do poprawnego działania systemu wymagane jest:
- Python 3.7 lub nowszy zainstalowany w systemie
- Zainstalowane biblioteki: pywin32, pyodbc, reportlab, configparser
- Sterownik ODBC dla SQL Server
- Dostęp do bazy danych Wapro Mag
- Drukarka termiczna (np. ZD421) skonfigurowana w systemie Windows

Aby rozpocząć korzystanie z systemu:
1. Umieść wszystkie pliki w wybranym katalogu (np. C:\WaproPrintSystem)
2. Uruchom skrypt install.bat z uprawnieniami administratora
3. Wybierz opcję 1 aby zainstalować usługę
4. Wybierz opcję 2 aby uruchomić usługę

Po wykonaniu tych kroków, system będzie automatycznie monitorował bazę danych i drukował nowe dokumenty ZO.



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
   C:\Users\[USERNAME]\wapromag\venv\Scripts\python.exe -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases


3. Start the server:
```bash
python html2zpl2pdf.py
```

The main differences are:
- In Windows, the Python command is typically just `python` instead of `python3`
- The virtual environment activation path uses backslashes and is located in the Scripts directory
- The activation command doesn't use `source` in Windows

Would you like any further adjustments to these commands for your Windows environment?


## LINUX

1. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install requirements:
   ```bash
   pip install --upgrade pip
   python.exe -m pip install --upgrade pip

   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   python html2escpos5.py zamowienie.html --width 60 --small-font 1 --encoding cp852
   ```
   
```bash
pip install pywin32 beautifulsoup4 pillow qrcode pyodbc configparser weasyprint reportlab PyPDF2 PyMuPDF numpy html2text escpos tabulate cssutils tinycss zebrafy
```

```bash
python sql2html.py
```



```
python html2zpl1.py zamowienie.html --printer "ZDesigner GK420d"
python zpl/html2zpl.py ZO_HTML/ZO_0023_25.html --printer "ZDesigner GK420d"
python zpl/html2zpl.py ZO_HTML/ZO_0023_25.html
python zpl/html2zpl1.py zamowienie.html
python zpl/html2zpl2pdf.py 
python zpl/html2zpl2print.py
```




















## Użycie

### Podstawowe użycie

```bash
python html_to_continuous_pdf.py
python html_to_continuous_pdf.py input.html -o output.pdf
```

### Wszystkie opcje [html_to_continuous_pdf_file_fix.py](html_to_continuous_pdf.py)

```bash
python html_to_continuous_pdf.py input.html --output output.pdf --width 4.0 --margin 5 --dpi 203 --items 34 --verbose
```

### Opcje

- `input_file`: Ścieżka do pliku HTML
- `-o, --output`: Ścieżka do pliku wyjściowego PDF (opcjonalnie, domyślnie nazwa taka jak plik wejściowy z rozszerzeniem .pdf)
- `--width`: Szerokość strony w calach (domyślnie 4.0)
- `--margin`: Margines w milimetrach (domyślnie 5)
- `--dpi`: Roz# Skrypt konwersji HTML do ciągłego PDF dla drukarek termicznych

Ten skrypt rozwiązuje problem konwersji plików HTML do formatu PDF w sposób ciągły (bez podziału na strony) - idealny dla drukarek termicznych i innych zastosowań, gdzie potrzebny jest dokument bez podziału na strony.

## Główne funkcje

1. **Generowanie PDF o dokładnej długości treści** - dokument będzie tak długi, jak jego zawartość, bez zbędnej białej przestrzeni
2. **Dwuprzebiegowa konwersja** - pierwszy przebieg tworzy PDF do analizy, drugi przebieg generuje PDF o dokładnej wysokości
3. **Automatyczne wykrywanie końca dokumentu** - skrypt wykrywa gdzie faktycznie kończy się treść
4. **Obsługa problematycznych formatowań** - eliminuje problemy z podziałami stron i nieprawidłowym formatowaniem HTML
5. **Elastyczne opcje rozmiaru i marginesów** - możliwość dostosowania do drukarek termicznych różnej szerokości

## Wymagania

- Python 3.6 lub nowszy
- Biblioteka PyPDF2: `pip install PyPDF2`
- wkhtmltopdf: [Pobierz i zainstaluj](https://wkhtmltopdf.org/downloads.html)

### Opcjonalne zależności (dla lepszej analizy PDF)
- PyMuPDF: `pip install PyMuPDF` (dokładniejsza analiza zawartości PDF)
- PIL i NumPy: `pip install pillow numpy` (analiza obrazu PDF)
- pdf2image: `pip install pdf2image` (konwersja PDF na obrazy do analizy)

## Instalacja

1. Zainstaluj wymagane zależności:
   ```
   pip install PyPDF2
   ```

2. Pobierz i zainstaluj wkhtmltopdf:
   - Dla Windows: Pobierz instalator z [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
   - Dla Linux: `sudo apt-get install wkhtmltopdf` (Ubuntu/Debian) lub odpowiednik dla Twojej dystrybucji
   - Dla macOS: `brew install wkhtmltopdf` (wymaga Homebrew)

3. Upewnij się, że wkhtmltopdf jest dostępny w ścieżce systemowej lub wskaż jego lokalizację w skrypcie.

## Użycie

### Podstawowe użycie

```bash
python html_to_pdf_cont.py input.html -o output.pdf
```

### Wszystkie opcje

```bash
python html_to_pdf_cont.py input.html --output output.pdf --width 4.0 --margin 5 --dpi 203 --items 34 --verbose
```

```bash
python html_to_continuous_pdf.py ZO_HTML/ZO_0020_25.html --output output.pdf --width 4.0 --margin 1 --dpi 203 --split-pdf --verbose  
```

### Opcje

- `input_file`: Ścieżka do pliku HTML
- `-o, --output`: Ścieżka do pliku wyjściowego PDF (opcjonalnie, domyślnie nazwa taka jak plik wejściowy z rozszerzeniem .pdf)
- `--width`: Szerokość strony w calach (domyślnie 4.0)
- `--margin`: Margines w milimetrach (domyślnie 5)
- `--dpi`: Rozdzielczość w DPI (domyślnie 203, typowa dla drukarek termicznych)
- `--items`: Liczba pozycji w dokumencie - pomaga obliczyć optymalną wysokość PDF (opcjonalnie)
- `--verbose, -v`: Wyświetlaj szczegółowe komunikaty

## Rozwiązywanie problemów

1. **Jeśli PDF jest generowany z podziałem na strony**:
   - Upewnij się, że używasz najnowszej wersji skryptu
   - Zwiększ wartość parametru `--width`, aby dostosować ją do szerokości Twojej drukarki

2. **Jeśli PDF ma białą przestrzeń na końcu**:
   - Może być to powodowane przez specyficzne style CSS w dokumencie HTML
   - Spróbuj edytować plik HTML aby usunąć elementy dodające dodatkową przestrzeń

3. **Jeśli wkhtmltopdf nie jest znajdowany**:
   - Upewnij się, że jest poprawnie zainstalowany
   - Dodaj ścieżkę do katalogu bin wkhtmltopdf do zmiennej PATH
   - Możesz też ręcznie zmodyfikować funkcję `find_wkhtmltopdf_path()` w skrypcie

## Jak to działa

1. Skrypt najpierw przetwarza plik HTML, dodając specjalne style CSS, które wymuszają ciągły format bez podziału na strony.
2. Następnie uruchamia wkhtmltopdf z odpowiednimi opcjami, aby wygenerować PDF.
3. Na końcu używa PyPDF2 do przetworzenia PDF, usuwając ewentualną nadmiarową białą przestrzeń i zapewniając odpowiedni format wyjściowy.

## Przykład zastosowania dla drukarek termicznych

Dla drukarki termicznej o szerokości 80mm (około 3.15 cala), możesz użyć:

```bash
python html_to_pdf_cont.py faktura.html --width 3.15 --margin 2 --dpi 203
```

Ten skrypt jest idealny do generowania:
- Paragonów i faktur
- Etykiet
- Długich list i raportów
- Dokumentów, które mają być drukowane na drukarkach termicznych

## Uwagi

- Niektóre skomplikowane układy HTML mogą nie konwertować się idealnie. W takich przypadkach warto uprościć HTML.
- Skrypt został zoptymalizowany do pracy z drukarkami termicznymi i podobnymi zastosowaniami wymagającymi ciągłego dokumentu.