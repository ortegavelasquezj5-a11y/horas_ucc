"""Conector de MySQL.

Se usa PyMySQL (escrito en Python puro) porque se instala en Windows sin
compilar nada. Estas líneas hacen que Django lo use como si fuera mysqlclient.
"""
try:
    import pymysql

    pymysql.version_info = (2, 2, 7, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # sin PyMySQL solo funciona el modo SQLite
    pass
