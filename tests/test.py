from bigsql import big_SQL
from bigsql.models import StaticModel
from bigsql.types import StaticColumn, Integer, Varchar, TimeStamp
from bigsql.err import big_ERROR
from datetime import datetime

import string
import random


def test():
    class Test(StaticModel):
        id=StaticColumn(Integer, primary_key=True, auto_increment=True)
        a_string=StaticColumn(Varchar(128))
        date=StaticColumn(TimeStamp)


    db=big_SQL(
        user='root',
        pword='password',
        host='127.0.0.1',
        db='TS',
    )

    db.create_all()

    username1=''.join(
        random.choice(string.ascii_letters)
        for _ in range(10)
    )
    username2=''.join(
        random.choice(string.ascii_letters)
        for _ in range(10)
    )

    admin=db.query('Person').new(username=username1)
    db.session.commit()

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username1)
        db.session.add(photo)

        db.session.rollback()

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username1)
        db.session.add(photo)

    db.session.commit()

    len1=len(list(admin.photos))

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username1)
        db.session.add(photo)

    db.session.commit()

    len2=len(list(admin.photos))

    assert len1 != len2

    for _ in range(1000):
        t=Test(a_string='abc')
        db.session.add(t)

    db.session.commit()

    for i in Test.query.find(a_string='abc').all():
        i.date = datetime.now()
        db.session.add(i)

    db.session.commit()

    for t in Test.query.find(a_string='abc').all():
        db.session.delete(t)

    db.session.commit()

    db.session.commit()

    db.sql.INSERT(username=username1).INTO('Person').ONDUPUPDATE().gen()
    db.sql.SELECTFROM('Photo').JOIN('Person').WHERE(username=username2).ORDERBY('username').GROUPBY('username').gen()

if __name__ == "__main__":
    test()
