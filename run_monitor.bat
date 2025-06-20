@echo off
# usun plik app.log
del app.log
:loop
    echo Uruchamianie sql2html.py...
    python sql2html.py
    timeout /t 5 /nobreak
goto loop