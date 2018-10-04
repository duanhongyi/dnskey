from django.conf import settings
from django.core.cache import cache

from dnskey import helper

class PrimaryReplicaRouter(object):
    def __init__(self):
        self.database_primary_list = [
            key for key in settings.DATABASES.keys() if key.startswith("primary")
        ]
        self.database_replica_list = [
            key for key in settings.DATABASES.keys() if key.startswith("replica")
        ]

    @property
    def database_whitelist(self):
        database_whitelist_keys = [
            "database_whitelist:%s" % key for key in self.database_replica_list
        ]
        database_whitelist_keys.extend([
            "database_whitelist:%s" % key for key in self.database_primary_list
        ])
        return set(cache.get_many(database_whitelist_keys).keys())

    def get_available_database(self, databases):
        database = random.choice(databases)
        database_whitelist = self.database_whitelist
        timeout = settings.DNSKEY_DATABASE_WHITELIST_TIMEOUT
        if database not in database_whitelist:
            if helper.check_tcp(
                settings.DATABASES[database]["HOST"],
                settings.DATABASES[database]["PORT"],
                timeout,
            ):
                cache.set(
                    "database_whitelist:%s" % database,
                    timeout,
                    timeout,
                )
                return database
            else:
                database = random.choice(list(
                    set(databases) & database_whitelist
                ))
        return database

    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly-chosen replica.
        """
        return self.get_available_database(self.database_replica_list)

    def db_for_write(self, model, **hints):
        """
        Writes always go to primary.
        """
        return self.get_available_database(self.database_primary_list)


    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All non-auth models end up in this pool.
        """
        return True