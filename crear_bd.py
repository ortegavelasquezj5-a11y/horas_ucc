"""Crea la base de datos horas_ucc en el MySQL de XAMPP si todavía no existe.

Requisito: MySQL encendido en el panel de control de XAMPP.
"""
import sys

import pymysql
from decouple import AutoConfig

config = AutoConfig(search_path=__file__.rsplit("crear_bd.py", 1)[0] or ".")
nombre = config("DB_NAME", default="horas_ucc")

try:
    conexion = pymysql.connect(
        host=config("DB_HOST", default="127.0.0.1"),
        port=int(config("DB_PORT", default="3306")),
        user=config("DB_USER", default="root"),
        password=config("DB_PASSWORD", default=""),
        charset="utf8mb4",
    )
except pymysql.err.OperationalError as error:
    print("No se pudo conectar a MySQL. ¿Está encendido MySQL en el panel de XAMPP?")
    print(f"Detalle: {error}")
    sys.exit(1)

with conexion.cursor() as cursor:
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{nombre}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
conexion.close()
print(f"Base de datos '{nombre}' lista en MySQL.")
