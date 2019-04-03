from bigsql import big_SQL
from bigsql.models import *
from bigsql.types import *

if __name__ == "__main__":
    class Test(BaseModel):
        id = Column(Integer, primary_key=True)
        a_string = Column(Varchar(128), references='Person.username')
        date = Column(DateTime)


    admin=Query.Query('Person').find(username='admin').first()
    for photo in admin.photos:
        photo.delete()
    # t = Test.query.find(test_name='abc').first()
    # print(t)