from dataclasses import dataclass

import pymysql.cursors

from . import bigsql
from . import err
from . import models


@dataclass
class TrackedObject(object):
    o: object
    initialized: bool=False


class ObjectTracker(object):
    def __init__(self):
        self.objects={}

    def __iter__(self):
        for table in self.objects:
            for tracked_o in self.objects[table].values():
                yield tracked_o

    def __contains__(self, o):
        table_key, object_key=self.make_key(o)
        return table_key not in self.objects or object_key not in self.objects[table_key]

    def add(self, o, initialized=False):
        """
        Will add object to tracking session if it is not already there.
        Will return the the object if it is new to the session, or object
        in the session.

        :param o:
        :param initialized:
        :return:
        """
        table_key, object_key=self.make_key(o)
        if table_key not in self.objects:
            self.objects[table_key]=dict()
        if object_key not in self.objects[table_key]:
            self.objects[table_key][object_key]=TrackedObject(
                o=o,
                initialized=initialized
            )
        return self.objects[table_key][object_key].o

    def clear(self):
        self.objects.clear()

    @staticmethod
    def make_key(o):
        table_key=o.__table__.name
        object_key=tuple(
            getattr(o, col.column_name)
            for col in o.__primary_keys__
        )
        return table_key, object_key


class Connection(object):
    """
    Simple wrapper for pymysql connections
    """

    def __init__(self, name):
        self.name=name
        self.conn=None
        self.cursor=None
        self.connect()

    def connect(self):
        self.conn=pymysql.connect(
            host=bigsql.config['host'],
            password=bigsql.config['pword'],
            user=bigsql.config['user'],
            db=bigsql.config['db'],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
            autocommit=False
        )
        self.conn.autocommit(False)
        self.cursor=self.conn.cursor()
        self.cursor.execute('SET autocommit = off;')
        self.begin_transaction()

    def close(self):
        self.cursor.close()
        self.conn.close()
        self.cursor=None
        self.conn=None

    def reset_cursor(self):
        self.cursor.close()
        self.cursor=None
        self.cursor=self.conn.cursor()
        self.cursor.execute('SET autocommit = off;')

    def begin_transaction(self):
        """
        begin transaction
        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='Executing: START TRANSACTION; {}'.format(self.name)
            bigsql.logging.info(msg)
        self.cursor.execute('START TRANSACTION ;')

    def commit_transaction(self):
        """
        commit transaction
        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='Executing: COMMIT; {}'.format(self.name)
            bigsql.logging.info(msg)
        # self.conn.commit()
        self.cursor.execute('COMMIT;')
        self.reset_cursor()
        self.begin_transaction()

    def rollback_transaction(self):
        """
        Rolls back transaction

        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='Executing: ROLLBACK;'
            bigsql.logging.info(msg)
        self.conn.rollback()
        self.reset_cursor()
        self.begin_transaction()

    def execute(self, sql, args=None):
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='Executing: {} {}'.format(sql, args)
            bigsql.logging.info(msg)
        self.cursor.execute(sql, args)
        return self.cursor


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
        self.object_tracker=ObjectTracker()

        self.orm_conn=Connection('mod')
        self.raw_conn=Connection('raw')

    def execute_raw(self, sql, args=None):
        """
        Will execute then give back all output rows.

        :param str sql: raw sql
        :param tuple args: iterable arguments
        :return:
        """
        r=self.raw_conn.execute(sql, args).fetchall()
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

        return self.object_tracker.add(
            o,
            initialized
        )

    def commit(self):
        """
        attempts to commit state of tracked items to the database

        :return:
        """
        self.orm_conn.commit_transaction()
        self.object_tracker.clear()

    def rollback(self):
        for o in self.object_tracker:
            o.o.__rollback__()
        self.orm_conn.rollback_transaction()
