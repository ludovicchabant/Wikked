import os
import os.path
import logging

try:
    import simplejson as json
except ImportError:
    import json


logger = logging.getLogger(__name__)


class Cache(object):
    def __init__(self, root):
        self.cache_dir = root

    def isValid(self, url, time):
        path, valid = self._getCachePathAndValidity(url, time)
        return valid

    def read(self, url, time):
        path, valid = self._getCachePathAndValidity(url, time)
        if valid:
            with open(path, 'r') as f:
                return json.load(f)
        return None

    def write(self, url, data):
        path = self._getCachePath(url)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, 'w') as f:
            json.dump(data, f)

    def remove(self, url):
        path = self._getCachePath(url)
        if os.path.isfile(path):
            os.remove(path)

    def getTime(self, url):
        path = self._getCachePath(url)
        if not os.path.isfile(path):
            return None
        return os.path.getmtime(path)

    def _getCachePath(self, url):
        return os.path.join(self.cache_dir, url)

    def _getCachePathAndValidity(self, url, time):
        cache_path = self._getCachePath(url)
        if not os.path.isfile(cache_path):
            return cache_path, False

        if time >= os.path.getmtime(cache_path):
            return cache_path, False

        return cache_path, True

