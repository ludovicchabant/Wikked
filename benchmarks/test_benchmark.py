import re
import urllib.parse
import random
import unittest
from funkload.FunkLoadTestCase import FunkLoadTestCase


class Benchmark(FunkLoadTestCase):
    """This test uses a configuration file Benchmark.conf."""
    def setUp(self):
        self.server_url = self.conf_get('main', 'url')

    def test_simple(self):
        server_url = self.server_url
        if not re.match('https?://', server_url):
            raise Exception("The `server_url` setting doesn't have a scheme.")

        username = self.conf_get('test_benchmark', 'username', None)
        password = self.conf_get('test_benchmark', 'password', None)
        if username and password:
            self.post(self.server_url + "/api/user/login",
                  params=[['username', username],
                          ['password', password]],
                  description="Login as %s" % username)

        nb_times = self.conf_getInt('test_benchmark', 'nb_times')
        names = self.conf_get('test_benchmark', 'page_names').split(';')
        for i in range(nb_times):
            r = random.randint(0, len(names) - 1)
            url = server_url + '/api/read/' + urllib.parse.quote(names[r])
            self.get(url, description='Getting %s' % names[r])


if __name__ in ('main', '__main__'):
    unittest.main()

