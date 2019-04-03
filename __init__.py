from web.bsql.BaseModel import BaseModel, TempModel
from web.bsql.Query import Query as query
from web.bsql.Sql import Sql, Table, JoinedTable
from web.bsql.types import Column, Integer, Text, Varchar, DateTime
from web.bsql.utils import strptime, classproperty


def create_all():
    """
    Generates all create table sql, then runs it for
    all models defined as subclasses of BaseModel.
    """
    for model_type in BaseModel.__subclasses__():
        if model_type == BaseModel.TempModel:
            continue
        raw = BaseModel.__gen_sql__(model_type)
        if raw is not None:
            Sql.Sql.execute_raw(
                raw
            )


if __name__ == "__main__":
    class Test(BaseModel):
        id = Column(Integer, primary_key=True)
        a_string = Column(Varchar(128), references='Person.username')
        date = Column(DateTime)


    admin=query('Person').find(username='admin').first()
    for photo in admin.photos:
        photo.delete()
    # t = Test.query.find(test_name='abc').first()
    # print(t)