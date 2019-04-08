from datetime import datetime, timedelta, timezone

class ClassPropertyDescriptor(object):
    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        return self.fget.__get__(obj, klass)()


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


def strptime(datestr):
    """
    Loads datetime from string for object
    """
    return datetime.strptime(datestr, '%Y-%m-%d %H:%M:%S')