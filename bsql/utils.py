from datetime import datetime, timedelta, timezone
from random import randint


class ClassPropertyDescriptor(object):
    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


def strptime(datestr):
    """
    Loads datetime from string for object
    """
    return datetime.strptime(datestr, '%Y-%m-%d %H:%M:%S')


def est_now():
    """
    Get EST now datetime object.

    .strftime('%Y-%m-%d %H:%M:%S')

    :return:
    """
    return datetime.now(tz=timezone(offset=timedelta(hours=-5)))


def gen_randint():
    return randint(0, 0xffffffffffffffff)
