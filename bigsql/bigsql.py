from . import Query
from . import models
from . import Sql
from . import session
from flaskext.mysql import MySQL

import logging
import os


logging.basicConfig(
    format='%(message)s',
    level='DEBUG'
)


class DefaultConfig:
    MYSQL_DATABASE_USER = 'root'
    MYSQL_DATABASE_PASSWORD = 'password'
    MYSQL_DATABASE_HOST = 'db'
    MYSQL_DATABASE_DB = 'TS'

    VERBOSE_SQL_GENERATION = False
    VERBOSE_SQL_EXECUTION = True

    SQL_CACHE_TIMEOUT = 5
    SQL_CACHE_ENABLED = True

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, item):
        return getattr(self, item) if item in self.__class__.__dict__ else None


class big_SQL:
    query=Query

    def __init__(self, app):
        global db

        for i in app.config:
            config[i] = app.config[i]
        db = MySQL(app)
        self.session=session.Session()

        if config['LOG_DIR'] is not None:
            logging.basicConfig(filename=os.path.join(
                config['LOG_DIR'],
                'orm_log.log'
            ), filemode='w+', level='DEBUG')

    @staticmethod
    def create_all():
        """
        Generates all create table sql, then runs it for
        all models defined as subclasses of BaseModel.
        """
        for model_type in models.BaseModel.__subclasses__():
            if model_type == models.BaseModel.TempModel:
                continue
            raw = models.BaseModel.__gen_sql__(model_type)
            if raw is not None:
                Sql.Sql.execute_raw(
                    raw
                )


config=DefaultConfig()
db=None
