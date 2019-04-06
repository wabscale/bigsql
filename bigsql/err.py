import pymysql.err

class big_ERROR(pymysql.err.IntegrityError):
    pass