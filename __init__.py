from web.bsql.BaseModel import BaseModel, TempModel
from web.bsql.Query import Query
from web.bsql.Sql import Sql, Table, JoinedTable
from web.bsql.types import Column, Integer, Text, Varchar, DateTime
from web.bsql.utils import strptime, classproperty
from web.bsql.bsql import BSQL

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