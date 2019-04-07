# big_SQL
big_SQL is an ORM features dynamic model generation, with on the fly relationship detection and resolution. 
It uses a high level custom sql generator in its backend.

### Static generation
To use the static models with bigSQL, all you need to do define your models same as other ORMs:
```python
from bigsql import *

class Test(StaticModel):
    id = StaticColumn(Integer, primary_key=True, auto_increment=True)
    a_string = StaticColumn(Varchar(128), references="Person.username")
    date = StaticColumn(DateTime)

db = big_SQL(
    user='root',
    pword='password',
    host='127.0.0.1',
    db='DB',
)

db.create_all()

t = Test(a_string='a string')

db.session.add(t)

try:
    db.session.add(t)
    db.session.commit()
except big_ERROR as e:
    print('onooooooz', e)
    db.session.rollback()

```

### Static querying
After we create an object, we will more than likely want to use it again at some point.
Here is how you can query, modify then commit statically defined models
```python
from bigsql import *
from datetime import datetime

class Test(StaticModel):
    id = StaticColumn(Integer, primary_key=True, auto_increment=True)
    a_string = StaticColumn(Varchar(128))
    date = StaticColumn(DateTime)

db = big_SQL(
    user='root',
    pword='password',
    host='127.0.0.1',
    db='DB',
)

db.create_all()

# to query then modify an object
t = Test.query.find(a_string='a string').first()

t.date = datetime.now()

try:
    db.session.commit()
except big_ERROR as e:
    print('onooooooz', e)
    db.session.rollback()
    
# To delete an object:
t = Test.query.find(a_string='another string').first()

db.session.delete(t)

try:
    db.session.commit()
except big_ERROR as e:
    print('onooooooz', e)
    db.session.rollback()

``` 



### Dynamic generation

#### Models
The really cool thing this ORM does is dynamic model generation. 
If you already have a database with tables defined, you can 
just query existing tables, and bigsql will generate models for you.

#### Relationships
If you have a defined foreign key relationship with another table 
already defined, you don't need to tell bigsql about them. For an object 
with foreign models, you can just access it as a attribute, and it will 
hand you an iterable object with all the associated object for the 
current model (either dynamically or statically generated).

For example:

```python

""" Person structure
CREATE TABLE Person
(
    username  VARCHAR(20),
    PRIMARY KEY (username)
);
"""

""" Photo structure
CREATE TABLE Photo
(
    photoID      int NOT NULL AUTO_INCREMENT,
    photoOwner   VARCHAR(20),
    PRIMARY KEY (photoID),
    FOREIGN KEY (photoOwner) REFERENCES Person (username) ON DELETE CASCADE
);
"""

from bigsql import *

db = big_SQL(
    user='root',
    pword='password',
    host='127.0.0.1',
    db='DB',
)

# new_photo will be a dynamically generated model object
admin = db.query('Person').new(username='admin')
# new_photo will be a dynamically generated model object
new_photo = db.query('Photo').new(photoOwner='admin')

db.session.add(admin)
db.session.add(new_photo)

try:
    db.session.commit()
except big_ERROR as e:
    print('onooooooz', e)
    db.session.rollback()

# the relationship will be detected between Photo and Person, 
# so you can access either .photo or .photos on a Person object
# and you will get all the associated photos for this user as a list
admins_photos = list(admin.photos)
```

### Sql Engine

The query engine is quite simple and easy to use. It sports the fluent influence style for readability. 

```python
from bigsql import *

db = big_SQL(
    user='root',
    pword='password',
    host='127.0.0.1',
    db='DB',
)

# admin will be a dynamically generated model object
admin = db.sql.SELECTFROM('Person').WHERE(username='admin').first()

# new_user will be a dynamically generated model object
new_user = db.sql.INSERT(username='new_user').INTO('Person').do()

# to get the raw sql being generated for a query
raw_sql, args = db.sql.SELECTFROM('Photo').JOIN('Person').WHERE(username='admin').gen()

```

# Maintainer
- big_J | john@bigj.icu
