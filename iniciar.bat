@echo off
echo Recuerda: MySQL debe estar encendido en el panel de XAMPP.
echo Iniciando el sistema... el navegador se abrira solo cuando la pagina este lista.
call venv\Scripts\activate
start "" /min powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){try{Invoke-WebRequest http://127.0.0.1:8000/login/ -UseBasicParsing -TimeoutSec 2 | Out-Null; break}catch{Start-Sleep 1}}; Start-Process http://127.0.0.1:8000/"
python manage.py runserver
