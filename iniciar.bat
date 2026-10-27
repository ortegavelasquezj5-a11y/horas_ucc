@echo off
chcp 65001 >nul
echo Recuerda: MySQL debe estar encendido en el panel de XAMPP.
call venv\Scripts\activate
start "" http://127.0.0.1:8000/
python manage.py runserver
