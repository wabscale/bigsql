from .types import Column, Integer, Text, Varchar, DateTime
from .BaseModel import BaseModel, TempModel
from .utils import strptime, classproperty
from .Sql import Sql, Table, JoinedTable
from .Query import Query
from .bigsql import BSQL

if __name__ == "__main__":
    class Test(BaseModel):
        id = Column(Integer, primary_key=True)
        a_string = Column(Varchar(128), references='Person.username')
        date = Column(DateTime)


    admin=Query('Person').find(username='admin').first()
    for photo in admin.photos:
        photo.delete()
    # t = Test.query.find(test_name='abc').first()
    # print(t)