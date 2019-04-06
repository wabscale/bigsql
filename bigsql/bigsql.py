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
    BIGSQL_USER = 'root'
    BIGSQL_PASSWORD = 'password'
    BIGSQL_HOST = '127.0.0.1'
    BIGSQL_DB = 'TS'

    VERBOSE_SQL_GENERATION = False
    VERBOSE_SQL_EXECUTION = True

    SQL_CACHE_TIMEOUT = 5
    SQL_CACHE_ENABLED = True

    def __iter__(self):
        yield from filter(
            lambda x: x.upper() == x,
            self.__class__.__dict__
        )


class big_SQL:
    def __init__(self, **kwargs):
        global config
        config={
            item: kwargs[item] if item in kwargs else getattr(DefaultConfig, item)
            for item in DefaultConfig()
        }
        self.session=session.Session()
        Query.session=self.session
        Sql.Sql.session=self.session

        self.query=Query.Query
        self.sql=Sql.Sql

        if 'LOG_DIR' in config:
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
        for model_type in models.DynamicModel.__subclasses__():
            if model_type == models.TempModel:
                continue
            raw = models.DynamicModel.__table_sql__(model_type)
            if raw is not None:
                Sql.Sql.session.execute_raw(
                    raw
                )


config=None