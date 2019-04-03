import pymysql.cursors
from . import bigsql


class Connection(object):
    """
    Simple wrapper for pymysql connections
    """
    def __init__(self, name):
        self.name = name
        self.conn = pymysql.connect(
            host=config.MYSQL_DATABASE_HOST,
            password=config.MYSQL_DATABASE_PASSWORD,
            user=config.MYSQL_DATABASE_USER,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        return self.cursor

    def close(self):
        self.conn.close()

    def commit(self):
        self.conn.commit()


class Session:
    """
    Session should handle trasactions for the connections
    and execute sql as needed for operations. Most important
    operations should be add commit and rollback.

    self.mod_conn : connection for handling object modification sql
    self.add_conn : connection for handling the creation of new entries
    self.raw_conn : connection for handing raw execution
    """
    def __init__(self):
        self.mod_conn = Connection()
        self.add_conn = Connection()
        self.raw_conn = Connection()

        self.mod_conn.execute("START TRANSACTION;")
        self.add_conn.execute("START TRANSACTION;")

    def add(self, obj):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def execute_raw(self, query):
        pass

