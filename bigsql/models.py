from . import Query
from . import Sql
from . import types
from . import utils
from . import bigsql

from copy import deepcopy


class DynamicModel(object):
    """
    All subclasses just need to define their own __name__
    to be the name of the table (along with any other convince
    methods).
    """
    __column_info__: list = None
    __relationships__: dict = None
    __primary_keys__: tuple = None

    class ModelError(Exception):
        pass

    class EmptyValue:
        pass

    class Relationship:
        """
        class BaseModel:
            __name__='Person'
            __relationships__={
                'photos': 'Photo'
            }
        """

        def __init__(self, model_obj, foreign_table):
            self.model_obj = model_obj
            self.foreign_table = Sql.Table(foreign_table)
            self._objs = None

        def __iter__(self):
            """
            yeild foreign table object specified my relationship
            :return:
            """

            if self._objs is None:
                ref, curr = Sql.JoinedTable.resolve_attribute(
                    self.foreign_table.name,
                    self.model_obj.__name__,
                )

                self._objs = Sql.Sql.SELECTFROM(
                    self.foreign_table.name
                ).JOIN(self.model_obj.__name__).WHERE(
                    '{table}.{primarykey}={value}'.format(
                        table=self.foreign_table.name,
                        primarykey=ref,
                        value=self.model_obj.__getattr__(curr)
                    )
                ).all()

            yield from self._objs

    def __init__(self, **kwargs):
        """
        Will fetch names of columns when initially called.

        :param list args: list of data members for object in order they were created.
        """
        self.__table__ = Sql.Table(self.__name__)
        self.__column_info__ = self.__table__.columns
        self.__relationships__ = self.__table__.relationships
        self.__lower_relationships__ = list(map(
            lambda rel: rel.lower(),
            self.__relationships__
        ))
        self.__column_lot__ = {
            col.column_name: col
            for col in self.__column_info__
        }
        self.__primary_keys__ = tuple(filter(
            lambda column: column.primary_key,
            self.__column_info__
        ))

        self.__original_state__=kwargs
        self.__current_state__=deepcopy(kwargs)
        self.__set_model_state__(**kwargs)

    def __str__(self):
        return '<{}Model: {}>'.format(
            self.__name__,
            '{{\n{}\n}}'.format(',\n'.join(
                '    {:12}: {}'.format(
                    col.column_name,
                    str(getattr(self, col.column_name))
                )
                for col in self.__column_info__
            ))
        )

    def __setattr__(self, key, value):
        """
        Overriding this method is necessary because the models state needs to
        be update in the database if a column attribute is modified.
        """
        if 'primary_keys' in self.__dict__ and key in self.__dict__['primary_keys']:
            raise self.__dict__['ModelError']('Unable to modify primary key value')
        if '__current_state__' in self.__dict__ and key in self.__current_state__:
            self.__current_state__[key] = value
            Sql.Sql.session.orm_conn.execute(*self.__update_sql__)

        self.__dict__[key] = value

    def __getattr__(self, item):
        """
        Relationship resolution happens here. If item is the name
        of a table that has a reference to the current model, a self.Relationship
        obejct will be returned.

        Alternatively, if item is the name of a column for this model, its current
        value will be read out of self.__current_state__ and returned. Be warned
        that if the column attribute has not been set, it is likely that you will
        get a self.EmptyValue object returned.

        :return:
        """
        if item == '__name__':  # boy this is a messy fix
            return self.__class__.__name__

        if '__current_state__' in self.__dict__ and item in self.__current_state__:
            return self.__current_state__[item]

        if self.__lower_relationships__ is not None:
            if item in self.__lower_relationships__:
                return self.Relationship(
                    self,
                    item[0].upper() + item[1:]
                )
            elif item.endswith('s') and item[:-1] in self.__lower_relationships__:
                return self.Relationship(
                    self,
                    item[0].upper() + item[1:-1]
                )
        raise AttributeError('Attribute not found {}'.format(item))

    def __rollback__(self):
        """
        This rolls back the models state to the __original_state__ dictionary.
        __rollback__ will be called on all tracked models in the db.session if
        db.session.rollback is called.
        :return:
        """
        self.__current_state__ = deepcopy(self.__original_state__)

    def __set_model_state__(self, **kwargs):
        for col in self.__column_info__:
            self.__current_state__[col.column_name]=self.EmptyValue()
        for col, val in kwargs.items():
            self.__current_state__[col]=val

    @staticmethod
    def __table_sql__(class_type):
        columns = [
            value.set_name(item, class_type.__name__)
            for item, value in class_type.__dict__.items()
            if isinstance(value, types.StaticColumn)
        ]
        if len(columns) == 0:
            return None
        primary_sql=',\n    PRIMARY KEY ({})'.format(', '.join(map(
            lambda col: col.column_name,
            filter(
                lambda col: col.primary_key,
                columns
            )
        )))
        unique_cols=list(filter(
            lambda col: col.unique,
            columns
        ))
        uniqs=',\n    UNIQUE ({})'.format(', '.join(map(
            lambda col: col.column_name,
            unique_cols
        ))) if len(unique_cols) != 0 else ''
        ref_cols=[
            column
            for column in columns
            if column.references is not None
        ]
        refs=',\n' + ',\n'.join(
            ' ' * 4 + column.ref_sql
            for column in ref_cols
        ) if len(ref_cols) != 0 else ''

        base = 'CREATE TABLE IF NOT EXISTS {table_name} (\n{columns}{primarys}{refs}{uniqs}\n);'
        sql = base.format(
            table_name=class_type.__name__,
            columns=',\n'.join(
                ' ' * 4 + column.sql
                for column in columns
            ),
            primarys=primary_sql,
            refs=refs,
            uniqs=uniqs,
        )
        if bigsql.config['VERBOSE_SQL_GENERATION']:
            bigsql.logging.warning('Generated: {}'.format(sql))
        return sql

    @utils.classproperty
    def query(cls):
        return Query.Query(cls)

    @property
    def __insert_update__(self):
        return Sql.INSERT(**{
            key: value
            for key, value in self.__current_state__.items()
            if not isinstance(value, self.EmptyValue)
        }).INTO(
            self.__class__.__name__
        ).ONDUPUPDATE().gen()

    @property
    def __defined_columns__(self):
        yield from (
            value.set_name(item, value.__class__.__name__)
            for item, value in self.__class__.__dict__.items()
            if isinstance(value, types.StaticColumn)
        )

    @property
    def __dynamically_generated__(self):
        return len(list(self.__defined_columns__)) > 0

    @property
    def __insert_sql__(self):
        """
        Generates sql necessary for initializing element in database.

        :return: sql, args
        """
        return Sql.Sql.INSERT(**{
            key: value
            for key, value in self.__current_state__.items()
            if not isinstance(value, self.EmptyValue)
        }).INTO(
            self.__class__.__name__
        ).gen()

    @property
    def __update_sql__(self):
        """
        generate and execute sql to update object in db

        ** This will rely on primary keys to update the object. If
        primary keys are modified, this will likely crash.

        :return:
        """
        return Sql.Sql.UPDATE(self.__name__).SET(**{
            col.column_name: self.__getattr__(col.column_name)
            for col in self.__column_info__
            if not col.primary_key
        }).WHERE(**{
            col.column_name: self.__getattr__(col.column_name)
            for col in self.__column_info__
            if col.primary_key
        }).gen()

    @property
    def __delete_sql__(self):
        """
        delete object from database

        :return:
        """
        return Sql.Sql.DELETE(self.__name__).WHERE(**{
            col.column_name: self.__getattr__(col.column_name)
            for col in self.__column_info__
            if col.primary_key
        }).gen()

    @property
    def __modified__(self):
        return any(
            getattr(self, key) != self.__original_state__[key]
            for key in self.__original_state__
        )

    def __update_current_state(self):
        self.__original_state__ = deepcopy(self.__current_state__)



class TempModel(DynamicModel):
    """
    A temporary model
    """

    def __init__(self, table_name, **kwargs):
        self.__name__ = table_name
        super(TempModel, self).__init__(**kwargs)

    def __str__(self):
        return '<Temp{}Model: {}>'.format(
            self.__name__,
            '{{\n{}\n}}'.format(',\n'.join(
                '    {:12}: {}'.format(
                    col.column_name,
                    str(self.__current_state__[col.column_name])
                )
                for col in self.__column_info__
            ))
        )


class StaticModel(DynamicModel):
    def __init__(self, **kwargs):
        super(StaticModel, self).__init__(**kwargs)
        self.__current_state__ = deepcopy(kwargs)
        self.__initialize_state__()

    def __getattribute__(self, item):
        if '__column_info__' in super(StaticModel, self).__getattribute__('__dict__'):
            col_names = list(map(
                lambda col: col.column_name,
                super(StaticModel, self).__getattribute__('__column_info__')
            ))
            if item in col_names:
                return self.__getattr__(item)
        return super(StaticModel, self).__getattribute__(item)

    def __initialize_state__(self):
        m = Sql.Sql.INSERT(**{
            key: value
            for key, value in self.__current_state__.items()
            if not isinstance(value, self.EmptyValue)
        }).INTO(
            self.__class__.__name__
        ).do()
        for key, value in m.__current_state__.items():
            self.__current_state__[key] = value