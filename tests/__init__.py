import os
import os.path
import shutil
import unittest
from wikked.wiki import Wiki
from mock import MockWikiParameters, MockFileSystem


class WikkedTest(unittest.TestCase):
    def setUp(self):
        # Directory you can use for temporary files.
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

    def _getWikiFromStructure(self, structure):
        wiki = self.getWiki(use_db=False, fs_factory=lambda cfg: MockFileSystem(structure))
        wiki.start()
        return wiki


def format_link(title, url, missing=False, mod=None):
    res = '<a class=\"wiki-link'
    if missing:
        res += ' missing'
    res += '\" data-wiki-url=\"' + url + '\"'
    if mod:
        res += ' data-wiki-mod=\"' + mod + '\"'
    res += '>' + title + '</a>'
    return res

def format_include(url, args=None, mod=None):
    res = '<div class=\"wiki-include\" data-wiki-url=\"' + url + '\"'
    if mod:
        res += ' data-wiki-mod=\"' + mod + '\"'
    res += '>'
    if args:
        res += args
    res += "</div>\n"
    return res
