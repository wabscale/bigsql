from . import Query
from . import Sql
from . import types
from . import utils
from . import bigsql


class DynamicModel(object):
    """
    All subclasses just need to define their own __name__
    to be the name of the table (along with any other convince
    methods).
    """
    __column_info__: list = None
    __relationships__: dict = None
    __primary_keys__: list = None

    class ModelError(Exception):
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
        table = Sql.Table(self.__name__)
        self.__column_info__ = table.columns
        self.__relationships__ = table.relationships
        self.__lower_relationships__ = list(map(
            lambda rel: rel.lower(),
            self.__relationships__
        ))
        self.__column_lot__ = {
            col.column_name: col
            for col in self.__column_info__
        }
        self.__primary_keys__ = list(filter(
            lambda column: column.primary_key,
            self.__column_info__
        ))

        self.__set_model_state__(**kwargs)
        self.__original_state__=kwargs

    def __str__(self):
        return '<{}Model: {}>'.format(
            self.__name__,
            '{{\n{}\n}}'.format(',\n'.join(
                '    {:12}: {}'.format(
                    col.column_name,
                    str(self.__dict__[col.column_name])
                )
                for col in self.__column_info__
            ))
        )

    def __setattr__(self, key, value):
        if 'primary_keys' in self.__dict__ and key in self.__dict__['primary_keys']:
            raise self.__dict__['ModelError']('Unable to modify primary key value')
        self.__dict__[key] = value
        # setattr(self, key, value)

    def __getattr__(self, item):
        """
        this is where relationships will be lazily resolved.
        :return:
        """
        if item == '__name__':  # boy this is a messy fix
            return self.__class__.__name__
        if self.__lower_relationships__ is not None:
            if item in self.__lower_relationships__:
                self.__dict__[item] = self.Relationship(
                    self,
                    item[0].upper() + item[1:]
                )
                return self.__dict__[item]
            elif item.endswith('s') and item[:-1] in self.__lower_relationships__:
                self.__dict__[item] = self.Relationship(
                    self,
                    item[0].upper() + item[1:-1]
                )
                return self.__dict__[item]
        return super(DynamicModel, self).__getattribute__(item)

    @property
    def __modified__(self):
        return any(
            getattr(self, key) != self.__original_state__[key]
            for key in self.__original_state__
        )

    def __generate_relationships__(self):
        """
        :return:
        """
        for table_name in self.__relationships__:
            self.__setattr__(
                table_name,
                self.Relationship(self, table_name)
            )

    def __set_column_value__(self, column_name, value):
        col = self.__column_lot__[column_name]
        if value is not None:
            if col.data_type == 'timestamp' and type(value) == str:
                value = utils.strptime(value)
            elif col.data_type in ('int', 'tinyint'):
                value = int(value)
        self.__setattr__(col.column_name, value)

    def __set_model_state__(self, **kwargs):
        for col in self.__column_info__:
            self.__set_column_value__(col.column_name, None)
        for col, val in kwargs.items():
            self.__set_column_value__(col, val)

    @staticmethod
    def __table_sql__(class_type):
        columns = [
            value.set_name(item, class_type.__name__)
            for item, value in class_type.__dict__.items()
            if isinstance(value, types.Column)
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
    def __current_state__(self):
        return {
            col.column_name: getattr(self, col.column_name)
            for col in self.__defined_columns__
        }

    @property
    def __insert_update__(self):
        return Sql.INSERT(
            **self.__current_state__
        ).INTO(
            self.__class__.__name__
        ).ONDUPUPDATE().gen()

    @property
    def __defined_columns__(self):
        yield from (
            value.set_name(item, value.__class__.__name__)
            for item, value in self.__class__.__dict__.items()
            if isinstance(value, types.Column)
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
        return Sql.Sql.INSERT(
            **self.__current_state__
        ).INTO(
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
                    str(self.__dict__[col.column_name])
                )
                for col in self.__column_info__
            ))
        )
