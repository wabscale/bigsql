import logging
import os
import warnings

from . import Query
from . import Session
from . import Sql
from . import models

logging.basicConfig(
    format='%(message)s',
    level='DEBUG'
)


class DefaultConfig:
    VERBOSE_SQL_GENERATION=False
    VERBOSE_SQL_EXECUTION=True

    SQL_CACHE_TIMEOUT=5
    SQL_CACHE_ENABLED=True

    def __iter__(self):
        yield from filter(
            lambda x: x.upper() == x,
            self.__class__.__dict__
        )


class big_SQL:
    def __init__(self, user, pword, host, db, **kwargs):
        global config
        config={
            item: kwargs[item] if item in kwargs else getattr(DefaultConfig, item)
            for item in DefaultConfig()
        }
        config['user']=user
        config['pword']=pword
        config['host']=host
        config['db']=db

        self.session=Session.Session()
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for model_type in models.StaticModel.__subclasses__():
                raw=models.StaticModel.__table_sql__(model_type)
                if raw is not None:
                    Sql.Sql.session.execute_raw(
                        raw
                    )


config=None
