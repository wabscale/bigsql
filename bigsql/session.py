from . import bigsql
from . import models
from . import err
from dataclasses import dataclass
import pymysql.cursors
import warnings


class Connection(object):
    """
    Simple wrapper for pymysql connections
    """
    def __init__(self, name):
        self.name = name
        self.conn = pymysql.connect(
            host=bigsql.config['BIGSQL_HOST'],
            password=bigsql.config['BIGSQL_PASSWORD'],
            user=bigsql.config['BIGSQL_USER'],
            db=bigsql.config['BIGSQL_DB'],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        self.cursor = self.conn.cursor()

    def commit_transaction(self):
        """
        commit transaction
        :return:
        """
        self.conn.commit()

    def rollback_transaction(self):
        """
        Rolls back transaction

        :return:
        """
        self.conn.rollback()

    def execute(self, sql, args=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.cursor.execute(sql, args)
        return self.cursor

    def close(self):
        self.conn.close()


@dataclass
class TrackedObject(object):
    o: object
    initialized: bool = False

    def __hash__(self):
        return hash(str(self.o.__primary_keys__))


class Session(object):
    """
    Session should handle transactions for the connections
    and execute sql as needed for operations. Most important
    operations should be add commit and rollback.

    self.mod_conn : connection for handling object modification sql
    self.add_conn : connection for handling the creation of new entries
    self.raw_conn : connection for handing raw execution
    """
    def __init__(self):
        self.tracked_objects=set()

        self.orm_conn = Connection('mod')
        self.raw_conn = Connection('raw')

    def execute_raw(self, sql, args=None):
        """
        Will execute then give back all output rows.

        :param str sql: raw sql
        :param tuple args: iterable arguments
        :return:
        """
        r = self.raw_conn.execute(sql, args).fetchall()
        self.raw_conn.commit_transaction()
        return r


    def add(self, o, initialized=False):
        """
        Function that adds obj to session state. All it needs to do here
        is add it to self.tracked_objects so that it can be tracked.

        :param o:
        :param initialized:
        :return:
        """
        if not models.DynamicModel.__subclasscheck__(o.__class__):
            raise err.big_ERROR(
                'invalid object being added to session {}'.format(
                    o
                )
            )
        if o in map(lambda to: to.o, self.tracked_objects):
            raise err.big_ERROR('object already in session')
        self.tracked_objects.add(TrackedObject(
            initialized=initialized,
            o=o,
        ))

    def commit(self):
        """
        attempts to commit state of tracked items to the database

        :return:
        """
        for o in self.tracked_objects:
            sql = o.o.__update_sql__ if o.initialized else o.o.__insert_sql__
            self.orm_conn.execute(*sql)
            o.initialized = True
        self.orm_conn.commit_transaction()
        self.tracked_objects.clear()


    def rollback(self):
        self.orm_conn.rollback_transaction()
