@echo off
chcp 65001 >nul
echo === Instalando el Sistema de Gestion de Horas (Horas UCC) ===
echo.
echo Antes de seguir: abre el panel de control de XAMPP y pulsa "Start" en MySQL.
pause

if not exist venv python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || goto error

python crear_env.py
python crear_bd.py || goto error
python manage.py migrate || goto error
python manage.py datos_demo || goto error

echo.
echo === Instalacion terminada ===
echo Para abrir el sistema ejecuta: iniciar.bat
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Revisa que MySQL este encendido en XAMPP y vuelve a ejecutar instalar.bat
pause
exit /b 1
