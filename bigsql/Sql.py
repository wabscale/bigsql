import string
from dataclasses import dataclass

from scanf import scanf

from . import bigsql
from . import models
from . import types


class Table:
    column_info_sql='SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY ' \
                    'FROM INFORMATION_SCHEMA.COLUMNS ' \
                    'WHERE TABLE_NAME=%s ' \
                    'AND TABLE_SCHEMA=DATABASE();'
    relationship_info_sql='SELECT TABLE_NAME ' \
                          'FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ' \
                          'WHERE REFERENCED_TABLE_NAME=%s;'

    def __init__(self, name):
        self.name=name

        if name not in Sql.__cache__['tables']:
            self.columns=self._get_columns()
            self.primary_keys=tuple(filter(
                lambda column: column.primary_key,
                self.columns
            ))
            self.relationships=self._get_relationships()
            Sql.__cache__['tables'][name]=self
        else:
            self.columns=Sql.__cache__['tables'][name].columns
            self.primary_keys=Sql.__cache__['tables'][name].primary_keys
            self.relationships=Sql.__cache__['tables'][name].relationships

    def _get_columns(self):
        """
        :returns: list of columns for self.ref_table
        """
        return [
            types.StaticColumn(self.name, *r)
            for r in Sql.session.execute_raw(
                self.column_info_sql,
                (self.name,)
            )
        ]

    def _get_relationships(self):
        """
        :return: list of relationships for self.name
        """
        return list(map(
            lambda row: row[0],
            Sql.session.execute_raw(
                self.relationship_info_sql,
                (self.name,)
            )
        ))

    def __str__(self):
        """
        Purly convience.
        """
        return self.name


class JoinedTable(Table):
    """
    Provide this object with the name of the current table,
    and the table to join, and it will generate the sql to
    successfully join the tables together (with __str__).

    The sql generation is lazy
    """

    @dataclass
    class _JoinAttribute:
        name: str
        ref_name: str=None

        def is_same(self):
            return self.name == self.ref_name

    class JoinError(Exception):
        pass

    ref_info_sql='SELECT COLUMN_NAME, REFERENCED_COLUMN_NAME ' \
                 'FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ' \
                 'WHERE TABLE_NAME=%s ' \
                 'AND REFERENCED_TABLE_NAME=%s ' \
                 'AND TABLE_SCHEMA=DATABASE();'

    def __init__(self, current_table, ref_table):
        super(self.__class__, self).__init__(ref_table)
        self.current_table=current_table.name
        self.join_attr=None
        self.sql=None

    @staticmethod
    def resolve_attribute(current_table, foreign_table):
        raw=Sql.execute_raw(
            JoinedTable.ref_info_sql,
            (current_table, foreign_table,)
        )
        return None if len(raw) == 0 else raw[0]

    def _gen(self):
        """
        This will figure out foreign keys, then give back the proper
        sql to join the given tables.

        Errors will be raised if the join is not possible (if foreign
        keys not defined).
        """
        if self.sql is not None:
            return self.sql

        name, ref_name=self.resolve_attribute(self.current_table, self.name)

        self.join_attr=self._JoinAttribute(
            name=name,
            ref_name=ref_name
        )

        self.sql='JOIN {ref_table}'.format(
            ref_table=self.name
        ) if self.join_attr.is_same() else 'JOIN {ref_table} ON `{table}`.`{name}`=`{ref_table}`.`{ref_name}`'.format(
            table=self.current_table,
            ref_table=self.name,
            name=self.join_attr.name,
            ref_name=self.join_attr.ref_name,
        )
        return self.sql

    def __str__(self):
        return self._gen()


class Sql:
    """
    _type    : type of expression (select, insert, ...)
    _table   : str
    _tables  : [ self.Table ]
    _columns : str
    _joins   : [ str ]
    _where   : [ _Condition ]
    _attrs   : [ str ]

    _table: name of table being selected from
    _columns: names of columns being selected
    _joins: names of tables that are being joined
    _where: list of conditions to be applied
    _attrs: names of accessable attributes (foreign and local)

    bigsql.config['VERBOSE_SQL_GENERATION'] : bool
    __cache__   : dict
    """
    __sep__=' '

    __cache__={
        'tables': {},
    }
    session=None

    class ExpressionError(Exception):
        """
        Generic Exception, nothing special.
        """

    @dataclass
    class _Condition:
        attribute: str
        attribute_table: str
        value: str
        operator: str=None

        def __iter__(self):
            """
            This is here so that _Condition object can be unpacked
            """
            yield self.attribute
            yield self.attribute_table
            yield self.value
            yield self.operator

    @dataclass
    class _Attribute:
        table: str
        name: str

    def __init__(self):
        """
        Only needs to null out all the state attributes.
        """
        self._type=None
        self._table=None
        self._sql=None
        self._attrs=None
        self._result=None
        self._raw_append_values=None

        # SELECT
        self._columns=None
        self._joins=None
        self._conditions=None
        self._group_by_column=None
        self._order_by_column=None

        # INSERT
        self._insert_values=None
        self._on_dup_update=False

        # UPDATE
        self._updates_values=None

    def __iter__(self):
        """
        Purely convenience.

        With this you can iterate through SELECT results
        """
        if self._type != 'SELECT':
            raise self.ExpressionError(
                'Iteration not possible'
            )
        yield from self()

    def __call__(self, *args, **kwargs):
        return self.all()

    def __len__(self):
        """
        Length of results
        """
        if self._result is None:
            self()
        return len(self._result)

    def __enter__(self):
        """
        __enter__ called in with statement. The intended behavior is that you
        make your expression in the with, then use as to set it to a variable,
        and it will execute the expression, and set the result to the variable.
        """
        return self.all()

    def __del__(self, *_):
        pass

    def __hash__(self):
        return hash(str(self.gen()))

    def _resolve_attribute(self, attr_name, skip_curr=False):
        """
        This method will take an attribute name, and
        try to find the table it came from. It will search
        in order starting with self._table, then iterate
        through self._joins.
        """
        if attr_name == '*':
            return self._table.name
        if not skip_curr:
            for column in self._table.columns:
                if column.column_name == attr_name:
                    return self._table.name
        if self._joins is not None:
            for joined_table in self._joins:
                for column in joined_table.columns:
                    if column.column_name == attr_name:
                        return joined_table.name
        raise self.ExpressionError(
            'Unable to resolve column name {}'.format(attr_name)
        )

    def _add_condition(self, clause, *specified_conditions, **conditions):
        """
        conditions will be resolved, while specified_conditions will not

        specfied_conditions will need to be of the form:
            '<table>.<column>=<value>'
            'Person.username=john'

        conditions will need to be of the form:
            <column>=<value>
            username=value

        :param clause: 'AND' or 'OR'
        :param specified_conditions: for when you want to be specific about conditions
        :param conditions: conditions that will be resolved
        """
        if self._conditions is None:
            self._conditions=[]

        if self._type not in ('SELECT', 'UPDATE', 'DELETE') or self._table is None:
            raise self.ExpressionError(
                'Expression Type error'
            )

        for condition in specified_conditions:
            table, attribute, value=scanf('%s.%s=%s', condition)

            if all(c in string.digits for c in value):
                value=int(value)

            if value in ('True', 'False'):
                value=1 if value == 'True' else 0

            self._conditions.append(
                self._Condition(
                    operator=clause,
                    attribute=attribute,
                    attribute_table=table,
                    value=value,
                )
            )

        for attribute, value in conditions.items():
            attribute_table=self._resolve_attribute(attribute)
            self._conditions.append(
                self._Condition(
                    operator=clause,
                    attribute=attribute,
                    attribute_table=attribute_table,
                    value=value,
                )
            )

    def _generate_attributes(self):
        """
        Will fill self._attributes with self._Attributes for
        self._table and joined tables.
        """
        column_info_sql='SELECT COLUMN_NAME ' \
                        'FROM INFORMATION_SCHEMA.COLUMNS ' \
                        'WHERE TABLE_NAME=%s ' \
                        'AND TABLE_SCHEMA=DATABASE();'
        joined_tables=list(map(
            lambda jt: jt.ref_table,
            self._joins
        )) if self._joins is not None else []
        all_tables=joined_tables + [self._table]
        for table_name in all_tables:
            current_table_attrs=Sql.execute_raw(column_info_sql, table_name)
            for attr in map(lambda x: x[0], current_table_attrs):
                self._attrs.append(
                    self._Attribute(
                        table=table_name,
                        name=attr,
                    )
                )

    def _generate_conditions(self):
        """
        This will hand back the sql as a string, and the
        args to fill the prepared placeholders

        ex:

        self._generate_conditions()
        ->
        "WHERE id=%i", (1,)
        """
        return (Sql.__sep__ + Sql.__sep__.join(
            '{operator} `{table}`.`{attr}` = %s'.format(
                operator=operator,
                table=table,
                attr=attr,
            )
            for attr, table, value, operator in self._conditions
        ), [
                    value if type(value) != bool else int(value)
                    for _, _, value, _ in self._conditions
                ]) if self._conditions is not None else ('', [])

    def _generate_joins(self):
        """
        This method will hand back the sql for the
        joins in the expression.
        """
        return Sql.__sep__ + Sql.__sep__.join(
            str(joined_table)
            for joined_table in self._joins
        ) if self._joins is not None else ''

    def _generate_select_columns(self):
        return ', '.join('`{column_table}`.`{column_name}`'.format(
            column_table=self._resolve_attribute(column_name),
            column_name=column_name
        ) for column_name in self._columns) if self._columns != ['*'] else '*'

    def _generate_groupby(self):
        return Sql.__sep__ + 'GROUP BY `{table_name}`.`{column_name}`'.format(
            table_name=self._resolve_attribute(self._group_by_column),
            column_name=self._group_by_column,
        ) if self._group_by_column is not None else ''

    def _generate_orderby(self):
        return Sql.__sep__ + 'ORDER BY `{table_name}`.`{column_name}`'.format(
            table_name=self._resolve_attribute(self._order_by_column),
            column_name=self._order_by_column,
        ) if self._order_by_column is not None else ''

    def _generate_select(self):
        """
        Handle generation of sql for select expression.

        :return: sql_str, (args,)
        """
        if self._type != 'SELECT' or self._columns is None or self._table is None:
            raise self.ExpressionError(
                'Expression state incomplete'
            )

        base='SELECT {columns}' + Sql.__sep__ + 'FROM {table}{joins}{conditions}{groupby}{orderby}'

        table='`{table}`'.format(table=self._table)
        columns=self._generate_select_columns()
        conditions, args=self._generate_conditions()
        joins=self._generate_joins()
        groupby=self._generate_groupby()
        orderby=self._generate_orderby()

        return base.format(
            conditions=conditions,
            columns=columns,
            table=table,
            joins=joins,
            groupby=groupby,
            orderby=orderby,
        ), args

    def _generate_insert(self):
        """
        This should hand back the prepared sql, and args for the insert values.
        """
        if self._type != 'INSERT' or self._table is None or self._insert_values is None:
            raise self.ExpressionError(
                'Expression state incomplete'
            )

        table=self._table
        columns=', '.join('`{column_name}`'.format(
            column_name=column_name
        ) for column_name in self._insert_values.keys())
        values=', '.join(
            ['%s'] * len(list(self._insert_values.values()))
        )
        ondup=self._generate_on_dup_update()

        base='INSERT INTO `{table}`' + Sql.__sep__ + \
             '({columns})' + Sql.__sep__ + \
             'VALUES ({values})' + Sql.__sep__ + \
             '{ondup}'
        insert_sql=base.format(
            columns=columns,
            values=values,
            table=table,
            ondup=ondup,
        )

        return insert_sql, list(
            value if type(value) != bool else int(value)
            for value in self._insert_values.values()
        )

    def _generate_on_dup_update(self):
        if not self._on_dup_update:
            return ''
        base='ON DUPLICATE KEY UPDATE {}'
        return base.format(
            Sql.__sep__.join(
                '{col_name}=VALUES({col_name})'.format(col_name=col_name)
                for col_name in self._insert_values.keys()
            )
        )

    def _generate_set_values(self):
        """
        generates the condition
        :return:
        """
        return ', '.join(
            '`{column}`=%s'.format(
                column=column
            )
            for column in self._updates_values.keys()
        ), list(self._updates_values.values())

    def _generate_update(self):
        """
        generates sql statement for UPDATE expression
        :return:
        """
        if self._type != 'UPDATE' or self._table is None or self._updates_values is None:
            raise self.ExpressionError(
                'Expression state incomplete'
            )

        table=self._table
        values, args1=self._generate_set_values()
        conditions, args2=self._generate_conditions()

        base='UPDATE `{table}` SET {values}{conditions}'

        return base.format(
            table=table,
            values=values,
            conditions=conditions
        ), args1 + args2

    def _generate_insert_select(self):
        """
        after we run an insert, we would like to get that new row,
        and turn it into a model. Here we will need to determine if
        primary keys were inserted, or generated then create a select
        statement to get that new row out.

        :return: sql str
        """

        if all(pkey.column_name in self._insert_values for pkey in self._table.primary_keys):
            sql, args=Sql.SELECTFROM(self._table.name).WHERE(**self._insert_values).gen()
        else:
            sql, args=Sql.SELECTFROM(self._table.name).gen()
            sql=sql[:-1]  # cut off
            sql+=Sql.__sep__ + 'WHERE {}=LAST_INSERT_ID()'.format(
                str(self._table.primary_keys[0])
            )
        if bigsql.config['VERBOSE_SQL_EXECUTION']:
            msg='Executing: {} {}'.format(sql, args)
            bigsql.logging.info(msg)

        return sql, args

    def _generate_delete(self):
        """
        generate sql for delete statement
        :return:
        """
        table=self._table.name
        conditions, args=self._generate_conditions()
        base='DELETE FROM {table}{conditions}'

        return base.format(
            table=table,
            conditions=conditions
        ), args

    @staticmethod
    def _resolve_model(table_name):
        """
        Resolve the name of the table as a
        string to a DynamicModel (else None).

        :param table_name: name of table to be resolved
        :return: subclass of DynamicModel or None
        """
        sub_models=models.DynamicModel.__subclasses__()
        for model in sub_models:
            if model.__name__ == table_name:
                return model
        return models.TempModel

    @property
    def extra_raw(self):
        """
        Flattens self._raw_appened_values into usable form for executing.
        :return:
        """
        if self._raw_append_values is None:
            self._raw_append_values=[]
        return Sql.__sep__.join(map(
            lambda x: x[0],
            self._raw_append_values
        )), list(map(
            lambda x: x[1],
            self._raw_append_values
        ))

    def gen(self):
        """
        This should take the object state, and convert it
        into a functioning sql statement, along with its arguments.

        This will hand back the sql statement, along with
        the args for it in a tuple.

        :return: sql_str, (args,)
        """
        if self._sql is None:
            raw_extra_sql, raw_extra_args=self.extra_raw
            sql, args={
                'SELECT': self._generate_select,
                'INSERT': self._generate_insert,
                'UPDATE': self._generate_update,
                'DELETE': self._generate_delete,
            }[self._type]()
            self._sql=(
                sql + raw_extra_sql + ';',
                args + raw_extra_args,
            )

            if bigsql.config['VERBOSE_SQL_GENERATION']:
                msg='Generated: {} {}'.format(*self._sql)
                bigsql.logging.info(msg)
        return self._sql

    def append_raw(self, sql, args=None):
        """
        You can add any raw sql, along with its args here

        :param sql:
        :param args:
        :return:
        """
        if self._raw_append_values is None:
            self._raw_append_values=[]
        if args is None:
            args=[]
        self._raw_append_values.append([
            sql, args
        ])
        return self

    def _generate_models(self, *results):
        Model=self._resolve_model(self._table.name)
        model_init_kwargs=[
            {
                col.column_name: val
                for col, val in zip(self._table.columns, item)
            }
            for item in results
        ]
        self._result=[
            Sql.session.add(
                Model(**kwargs),
                initialized=True
            )
            for kwargs in model_init_kwargs
        ] if Model is not models.TempModel else [
            Sql.session.add(
                Model(self._table.name, **kwargs),
                initialized=True
            )
            for kwargs in model_init_kwargs
        ]
        return self._result

    def first(self):
        """
        :return: first element of results
        """
        res=self.all()
        return res[0] if len(res) != 0 else None

    def all(self):
        """
        This method should generate the sql, run it,
        then hand back the result (if expression type
        is SELECT).

        ** importaint to note that this does not
        handle pymysql.err.IntegrityError's

        ** If the expression type is a SELECT, the
        return value will be cursor.fetchall()

        *** If you select * out of a table, this will
        give you a list of initialized models. If the model
        has not been defined already, it will create a temporary
        model for you.
        """
        self.gen()

        raw_result=Sql.session.execute_raw(*self._sql)

        if self._type in ('SELECT', 'INSERT'):
            if self._type == 'INSERT':
                sql=self._generate_insert_select()
                raw_result=Sql.session.execute_raw(*sql)

            result=self._generate_models(*raw_result)

        return result

    def do(self):
        """
        This is a cleaner name for insert queries to call to execute.

        :return: calls self.all()
        """
        return self.first()

    def WHERE(self, *specified_conditions, **conditions):
        """
        Errors will be raised if the type of this expression is not
        SELECT, or if a table has not been specified.

        If more than one condition is specified, it will by default
        apply AND logic between the conditions.
        """
        if self._type not in ('SELECT', 'UPDATE', 'DELETE') or self._table is None or self._conditions is not None:
            raise self.ExpressionError(
                'Expression Type error'
            )

        self._conditions=list()
        self._add_condition('AND', *specified_conditions, **conditions)
        self._conditions[0].operator='WHERE'
        return self

    def INTO(self, table):
        """
        Sets table for INSERT expression.
        """
        if self._type != 'INSERT':
            raise self.ExpressionError(
                'Expression Type error'
            )

        if self._table is not None:
            raise self.ExpressionError(
                'Table already set for INSERT expression'
            )

        self._table=Table(table)
        return self

    def FROM(self, table):
        """
        Adds table to select from to expression state
        """
        if self._type not in ('SELECT',) or self._table is not None:
            raise self.ExpressionError(
                'Expression Type error'
            )
        self._table=Table(table)
        return self

    def JOIN(self, *tables):
        """
        Adds joins to expression state for tables.
        """
        if self._type not in ('SELECT',) or self._table is None:
            raise self.ExpressionError(
                'Expression Type error'
            )
        if self._joins is None:
            self._joins=list()
        for table in tables:
            self._joins.append(
                JoinedTable(self._table, table)
            )
        return self

    def AND(self, *specified_conditions, **conditions):
        if len(self._conditions) == 0:
            raise self.ExpressionError(
                'Use where clause before applying an AND'
            )
        self._add_condition('AND', *specified_conditions, **conditions)
        return self

    def OR(self, *specified_conditions, **conditions):
        if len(self._conditions) == 0:
            raise self.ExpressionError(
                'Use where clause before applying an OR'
            )
        self._add_condition('AND', *specified_conditions, **conditions)
        return self

    def SET(self, **kwargs):
        if self._type not in ('SELECT', 'UPDATE'):
            raise self.ExpressionError(
                'Invalid Expression Type'
            )
        self._updates_values=kwargs
        return self

    def GROUPBY(self, column_name):
        """
        you can add a group by here

        * table name will be automatically resolved

        :param column_name:
        :return: self
        """
        if self._type not in ('SELECT',):
            raise self.ExpressionError(
                'Invalid Experssion Type'
            )
        self._group_by_column=column_name
        return self

    def ORDERBY(self, column_name):
        """
        add a orderby to expression

        * table name will be automatically resolved

        :param column_name:
        :return: self
        """
        if self._type not in ('SELECT',):
            raise self.ExpressionError(
                'Invalid Experssion Type'
            )
        self._order_by_column=column_name
        return self

    def ONDUPUPDATE(self):
        if self._type != 'INSERT':
            raise self.ExpressionError(
                'Invalid Expression Type'
            )
        self._on_dup_update=True
        return self

    @staticmethod
    def DELETE(table):
        e=Sql()
        e._type='DELETE'
        e._table=Table(table)
        return e

    @staticmethod
    def UPDATE(table):
        """

        :param table:
        :return:
        """
        e=Sql()
        e._type='UPDATE'
        e._table=Table(table)
        return e

    @staticmethod
    def INSERT(**values):
        """
        First method that should be called in INSERT expression.
        """
        e=Sql()
        e._type='INSERT'
        e._insert_values=values
        return e

    @staticmethod
    def SELECT(*columns):
        """
        All this does is set the type for the expression
        to SELECT and the columns being selected.

        This will throw and error if an expression type has already
        been specified.
        """
        e=Sql()
        e._type='SELECT'
        e._columns=[c for c in columns]
        return e

    @staticmethod
    def SELECTFROM(table):
        """
        Shortcut for SELECT('*').FROM('table')
        """
        return Sql.SELECT('*').FROM(table)

    @staticmethod
    def UNION(*expressions):
        gens=[
            e.gen()
            for e in expressions
        ]
        sql=' UNION '.join(map(
            lambda e: e[0],
            gens
        ))
        args=list(sum(map(
            lambda e: e[1],
            gens
        )))
        return Sql.execute_raw(
            sql, args
        )
