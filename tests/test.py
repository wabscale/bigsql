from bigsql import big_SQL
from bigsql.models import StaticModel
from bigsql.types import StaticColumn, Integer, Varchar, TimeStamp
from bigsql.err import big_ERROR

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
        host='db',
        db='TS',
    )

    db.create_all()

    username=''.join(
        random.choice(string.ascii_letters)
        for _ in range(10)
    )

    admin=db.query('Person').new(username=username)
    db.session.commit()

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username)
        db.session.add(photo)

        db.session.rollback()

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username)
        db.session.add(photo)

    db.session.commit()

    len1=len(list(admin.photos))

    for _ in range(1000):
        photo=db.query('Photo').new(photoOwner=username)
        db.session.add(photo)

    db.session.commit()

    len2=len(list(admin.photos))

    assert len1 != len2

    for _ in range(1000):
        t=Test(a_string='abc')
        db.session.add(t)

    db.session.commit()

    for t in Test.query.find(a_string='abc').all():
        db.session.delete(t)

    db.session.commit()

    try:
        db.session.commit()
    except big_ERROR:
        db.session.rollback()

if __name__ == "__main__":
    test()
