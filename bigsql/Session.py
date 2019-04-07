from dataclasses import dataclass

import pymysql.cursors

from . import bigsql
from . import err
from . import models


class ObjectTracker(object):
    """
    Data structure that tracks object in the current session.
    It indexes based on table, and the object primary keys.

    This structure is basically a radix tree.
    """
    def __init__(self):
        self.tree={}

    def __iter__(self):
        """
        Iterates over all tracked objects.
        :return:
        """
        for table in self.tree:
            for tracked_o in self.tree[table].values():
                yield tracked_o

    def __contains__(self, o):
        table_key, object_key=self.make_key(o)
        return table_key not in self.tree or object_key not in self.tree[table_key]

    def add(self, o):
        """
        Will add object to tracking session if it is not already there.
        Will return the the object if it is new to the session, or object
        in the session.

        :param o:
        :param initialized:
        :return:
        """
        table_key, object_key=self.make_key(o)
        if table_key not in self.tree:
            self.tree[table_key]=dict()
        if object_key not in self.tree[table_key]:
            self.tree[table_key][object_key]=o
        return self.tree[table_key][object_key]

    def delete(self, o):
        """
        Object needs to be removed from the object tracker, then
        the delete sql statement needs to be executed.
        """
        table_key, object_key=self.make_key(o)
        if table_key not in self.tree:
            self.tree[table_key]=dict()
        if object_key not in self.tree[table_key]:
            del self.tree[table_key][object_key]

    def clear(self):
        """
        Clears all object from session.
        Resets radix tree.

        :return:
        """
        for table_name in self.tree.keys():
            self.tree[table_name].clear()
        self.tree.clear()

    @staticmethod
    def make_key(o):
        """
        Makes keys for radix tree for initialized model o

        Keys are made based on models table, and primary keys.

        :param o:
        :return:
        """
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
        """
        Connect to database. This relies on the
        bigsql.config object.

        :return:
        """
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
        self.start_transaction()

    def close(self):
        """
        Closes cursor, then connection object.
        :return:
        """
        self.cursor.close()
        self.conn.close()
        self.cursor=None
        self.conn=None

    def reset_cursor(self):
        """
        Resets the current self.cursor.

        :return:
        """
        self.cursor.close()
        self.cursor=None
        self.cursor=self.conn.cursor()
        self.cursor.execute('SET autocommit = off;')

    def start_transaction(self):
        """
        starts transaction

        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='{} Executing: START TRANSACTION;'.format(self.name)
            bigsql.logging.info(msg)
        self.cursor.execute('START TRANSACTION ;')

    def commit_transaction(self):
        """
        commit transaction

        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='{} Executing: COMMIT;'.format(self.name)
            bigsql.logging.info(msg)
        # self.conn.commit()
        self.cursor.execute('COMMIT;')
        self.reset_cursor()
        self.start_transaction()

    def rollback_transaction(self):
        """
        Rolls back transaction

        :return:
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='{} Executing: ROLLBACK;'.format(self.name)
            bigsql.logging.info(msg)
        self.conn.rollback()
        self.reset_cursor()
        self.start_transaction()

    def execute(self, sql, args=None):
        """
        Executes raw sql through the current self.cursor.
        Autocommit is disabled by the connection object by default,
        so any changes that need to be reflected will need to be commited.

        :param str sql: raw sql statement
        :param tuple args: tuple of arguments for sql statement
        :return: self.cursor
        """
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='{} Executing: {} {}'.format(self.name, sql, args)
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

    def add(self, o):
        """
        Function that adds obj to session state. All it needs to do here
        is add it to self.tracked_objects so that it can be tracked.

        :param o: model object (dynamic or static)
        :return:
        """
        if not models.DynamicModel.__subclasscheck__(o.__class__):
            raise err.big_ERROR(
                'invalid object being added to session {}'.format(
                    o
                )
            )

        return self.object_tracker.add(o)

    def delete(self, o):
        """
        Removes object from object tracker (if is was being tracked)
        then executes its __delete_sql__ property.
        """
        self.object_tracker.delete(o)
        self.orm_conn.execute(o.__delete_sql__)

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
