import pymysql.cursors
from . import bigsql


class Connection(object):
    """
    Simple wrapper for pymysql connections
    """
    def __init__(self, name):
        self.name = name
        self.conn = pymysql.connect(
            host=bigsql.config.MYSQL_DATABASE_HOST,
            password=bigsql.config.MYSQL_DATABASE_PASSWORD,
            user=bigsql.config.MYSQL_DATABASE_USER,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        self.cursor = self.conn.cursor()

    def start_transaction(self):
        """
        starts transaction
        """
        self.cursor.execute('START TRANSACTION;')

    def commit_transaction(self):
        """
        commit transaction
        :return:
        """
        self.cursor.execute('COMMIT;')

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
        self.mod_conn = Connection('mod')
        self.add_conn = Connection('add')
        self.raw_conn = Connection('raw')

        self.mod_conn.start_transaction()
        self.add_conn.start_transaction()

    def add(self, obj):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def execute_raw(self, query):
        pass

