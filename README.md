å
# BSQL

BSQL features dynamic model creation, with on the fly relationship detection and resolution. 
It uses a high level custom sql query generator in its backend.

### Static generation
To use the static models with bsql, all you need to do define your models same as other ORMs:
```python
import bsql

# lets define a Test model
class Test(bsql.BaseModel):
    id = bsql.Column(bsql.Integer, primary_key=True)
    a_string = bsql.Column(bsql.Varchar(128), references='AnotherTable.column_name')
    date = bsql.Column(bsql.DateTime)


# creates all models in database
bsql.create_all()


# creates a new Test object
new_test=Test.query.new(id=1234)
# modify object 
new_test.a_string = 'some string'
# update its entry
new_test.update()


# find that same object later 
new_test=Test.query.find(id=1234).first()
# to delete object 
new_test.delete()
```


### Dynamic generation

#### Models
The really cool thing this ORM does is dynamic model generation. 
If you already have a database with tables defined, you can 
just query existing tables, and bsql will generate models for you.

#### Relationships
If you have a definded foreign key relationship with another table 
already defined, you don't need to tell bsql about them. For an object 
with foreign models, you can just access it as a attribute, and it will 
hand you a list of all objects (either dynamically or statically generated)
associated with the object. 

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

import bsql

admin = bsql.query.new(username='admin')
# new_photo will be a dynamically generated model object
new_photo = bsql.query('Photo').new(photoOwner='admin')

# the relationship will be detected between Photo and Person, 
# so you can access either .photo or .photos on a Person object
# and you will get all the associated photos for this user as a list
admins_photos = admin.photos
```

### Sql Engine

The query engine is quite simple and easy to use. It sports the fluent influence style for readability. 

```python
import bsql

# admin will be a dynamically generated model object
admin = bsql.Sql.SELECTFROM('Person').WHERE(username='admin').first()

# new_user will be a dynamically generated model object
new_user = bsql.Sql.INSERT(username='new_user').INTO('Person').do()

# to get the raw sql being generated for a query
raw_sql, args = bsql.Sql.SELECTFROM('Photo').JOIN('Person').WHERE(username='admin').gen()

```

# Maintainer
- big_J | john@bigj.icu
