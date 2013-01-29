import os
import os.path
import shutil
import unittest
from wikked.wiki import Wiki
from mock import MockWikiParameters


class WikkedTest(unittest.TestCase):
    def setUp(self):
        self.root = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'test_data')

    def tearDown(self):
        if hasattr(self, 'root') and os.path.isdir(self.root):
            shutil.rmtree(self.root)

    def getWiki(self, **kwargs):
        parameters = self.getParameters()
        for key in kwargs:
            setattr(parameters, key, kwargs[key])
        wiki = Wiki(parameters)
        return wiki

    def getStartedWiki(self, **kwargs):
        wiki = self.getWiki(**kwargs)
        wiki.start()
        return wiki

    def getParameters(self):
        return MockWikiParameters()
