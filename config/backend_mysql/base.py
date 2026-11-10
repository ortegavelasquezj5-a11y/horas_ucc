from django.db.backends.mysql import base, features
from django.utils.functional import cached_property


class DatabaseFeatures(features.DatabaseFeatures):
    # XAMPP trae MariaDB 10.4: se acepta esa version y se desactiva
    # INSERT ... RETURNING, que solo existe desde MariaDB 10.5.
    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return (8, 0, 11)

    @cached_property
    def can_return_columns_from_insert(self):
        return self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 5, 0)


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
