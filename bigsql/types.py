# from . import Sql
from dataclasses import dataclass

from scanf import scanf


@dataclass
class DataType:
    """
    Base datatype object. All defined types should inherit
    from this object.

    All this object should need is a name class variable.
    """
    name: str=None

    def __init__(self, length=None):
        if length is not None:
            self.name='{}({})'.format(
                self.name,
                length
            )


class Integer(DataType):
    name: str='INT'


class Text(DataType):
    name: str='TEXT'


class DateTime(DataType):
    name: str='DATETIME'


class TimeStamp(DataType):
    name: str='TIMESTAMP'


class Varchar(DataType):
    name: str='VARCHAR'


class StaticColumn:
    """
    StaticColumn holds information about user defined columns.
    This object should be used to define columns in statically defined models.

    This object is used to generate the column creation sql when db.create_all() is called.
    """
    column_name: str=None

    def __init__(self, data_type, **kwargs):
        self.data_type=data_type
        default_attrs={
            'primary_key'   : False,
            'nullable'      : False,
            'references'    : None,
            'on_delete'     : None,
            'auto_increment': False,
            'unique'        : False
        }

        for default_name, default_value in default_attrs.items():
            self.__setattr__(
                default_name,
                default_value \
                    if default_name not in kwargs \
                    else kwargs[default_name]
            )
        if self.references is not None:
            self.foreign_table, self.foreign_column=scanf('%s.%s', self.references)

    def __str__(self):
        return '`{}`.`{}`'.format(self.table_name, self.column_name)

    def set_name(self, name, table_name):
        self.column_name, self.table_name=name, table_name
        return self

    @staticmethod
    def resolve_type(type_name):
        return {
            'int'      : Integer,
            'tinyint'  : Integer,
            'text'     : Text,
            'varchar'  : Varchar(128),
            'timestamp': DateTime,
            'datetime' : DateTime,
        }[type_name]

    @property
    def sql(self):
        base='`{name}` {data_type}{auto_increment}{nullable}'
        return base.format(
            name=self.column_name,
            data_type=self.data_type.name,
            auto_increment=' AUTO_INCREMENT' if self.auto_increment else '',
            nullable=' NOT NULL' if not self.nullable else ' NULL'
        )

    @property
    def ref_sql(self):
        base='FOREIGN KEY ({name}) REFERENCES {foreign_table}({foreign_column}){on_delete}'
        return base.format(
            name=self.column_name,
            foreign_table=self.foreign_table,
            foreign_column=self.foreign_column,
            on_delete='ON DELETE {}'.format(
                self.on_delete
            ) if self.on_delete is not None else ''
        ) if self.references is not None else ''


@dataclass
class DynamicColumn(StaticColumn):
    def __init__(self, table_name, column_name, data_type, primary_key):
        super(DynamicColumn, self).__init__(
            self.resolve_type(data_type),
            primary_key=primary_key == 'PRI'
        )
        self.set_name(column_name, table_name)
