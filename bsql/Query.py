from . import BaseModel
from . import Sql


class Query(object):
    def __init__(self, table_name):
        self.table_name = table_name if isinstance(table_name, str) else table_name.__name__

    def find(self, **conditions):
        """
        similar to sqlalchemy's Sql.filter_by function

        :param conditions: list of conditions to find objects
        :return: Sql object
        """
        return Sql.Sql.SELECTFROM(self.table_name).WHERE(**conditions)

    def new(self, **values):
        """
        creates and inserts new element of type self.table_name

        :param values: key value dict for obj
        :return: new instance of table model
        """
        return Sql.Sql.INSERT(**values).INTO(self.table_name).do()

    def delete(self, **values):
        """
        deletes object from dateabase

        :param values:
        :return:
        """
        return Sql.Sql.DELETE(self.table_name).WHERE(**values).do()
