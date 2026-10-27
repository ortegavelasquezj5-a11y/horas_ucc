"""Crea el archivo .env con una clave secreta nueva (solo si aún no existe)."""
import secrets
from pathlib import Path

ruta = Path(__file__).resolve().parent / ".env"
if ruta.exists():
    print(".env ya existe: no se modifica.")
else:
    ruta.write_text(
        f"SECRET_KEY='{secrets.token_urlsafe(50)}'\n"
        "DEBUG=True\n"
        "ALLOWED_HOSTS=127.0.0.1,localhost\n"
        "\n"
        "# MySQL de XAMPP (por defecto el usuario root no tiene contraseña)\n"
        "DB_ENGINE=mysql\n"
        "DB_NAME=horas_ucc\n"
        "DB_USER=root\n"
        "DB_PASSWORD=\n"
        "DB_HOST=127.0.0.1\n"
        "DB_PORT=3306\n",
        encoding="utf-8",
    )
    print(".env creado con una clave secreta nueva.")
