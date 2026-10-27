"""Backend MySQL de Django adaptado a XAMPP.

XAMPP trae MariaDB 10.4 y Django 5.2 pide MariaDB 10.5 o superior. Lo único
que cambia este backend es esa versión mínima: las funciones que necesitan
10.5 Django ya las desactiva solo cuando detecta una versión anterior.
"""
from django.db.backends.mysql import base, features
from django.utils.functional import cached_property


class DatabaseFeatures(features.DatabaseFeatures):
    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return (8, 0, 11)


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
