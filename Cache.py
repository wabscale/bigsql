from dataclasses import dataclass
from datetime import datetime, timedelta

from ..app import app


@dataclass
class CachedQuery:
    """
    Object that stores the result of a cached query.
    """
    timestamp: datetime
    result: list

    @property
    def valid(self):
        timeout = app.config['SQL_CACHE_TIMEOUT']
        return datetime.now() - self.timestamp < timedelta(seconds=timeout)


class QueryCache:
    """
    This structure will essentially act as a dictionary, that stores
    cached queries
    """

    def __init__(self):
        self.__data__ = {}
        self.__access_counter__ = 0

    def __getitem__(self, item):
        self.purge_if_necessary()
        cache_id = self.gen_cache_id(item)
        return self.__data__[cache_id].result if cache_id in self.__data__ else None

    def __setitem__(self, key, value):
        self.purge_if_necessary()
        cache_id = self.gen_cache_id(key)
        self.__data__[cache_id] = CachedQuery(
            timestamp=datetime.now(),
            result=value
        )

    def __contains__(self, item):
        self.purge_if_necessary()
        return self.gen_cache_id(item) in self.__data__

    def purge_if_necessary(self):
        """
        Purges timed out entries for cached items. Timeout defined in
        config.py as SQL_CACHE_TIMEOUT.
        """
        if not self.time_to_purge:
            return
        to_purge = []
        for cache_id, value in self.__data__.items():
            if not value.valid:
                to_purge.append(cache_id)
        for item in to_purge:
            del self.__data__[item]

    @staticmethod
    def gen_cache_id(item):
        return hash(item)

    @property
    def time_to_purge(self):
        """
        Will return True every 10 time it is accessed
        """
        self.__access_counter__ += 1
        return self.__access_counter__ % 10 == 0
