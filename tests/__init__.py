import os
import os.path
import urllib.request, urllib.parse, urllib.error
import shutil
import unittest
from wikked.wiki import Wiki
from wikked.db.sql import SQLDatabase
from .mock import MockWikiParameters, MockFileSystem


class MockWikiParametersWithStructure(MockWikiParameters):
    def __init__(self, structure, root=None):
        super(MockWikiParametersWithStructure, self).__init__(root)
        self.structure = structure

    def fs_factory(self):
        return MockFileSystem(self.root, self.config, self.structure)


class WikkedTest(unittest.TestCase):
    def setUp(self):
        # Directory you can use for temporary files.
        self.test_data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'test_data')

    def tearDown(self):
        if hasattr(self, 'wiki') and self.wiki is not None:
            self.wiki.db.close(None)

        if os.path.isdir(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def _getParameters(self, root=None):
        return MockWikiParameters(root)

    def _getWiki(self, parameters=None, **kwargs):
        parameters = parameters or self._getParameters()
        for key in kwargs:
            setattr(parameters, key, kwargs[key])
        self.wiki = Wiki(parameters)
        self._onWikiCreated(self.wiki)
        return self.wiki

    def _getStartedWiki(self, **kwargs):
        wiki = self._getWiki(**kwargs)
        wiki.start()
        self._onWikiStarted(wiki)
        return wiki

    def _getWikiFromStructure(self, structure, root='/'):
        params = self._getParameters(root)
        params.fs_factory = lambda: MockFileSystem(
                params.root, params.config, structure)
        params.db_factory = lambda: SQLDatabase(params.config)
        params.config_text = "[wiki]\ndatabase_url = sqlite://\n"
        wiki = self._getStartedWiki(parameters=params)
        return wiki

    def _onWikiCreated(self, wiki):
        pass

    def _onWikiStarted(self, wiki):
        wiki.reset()


def format_link(title, url, missing=False, mod=None):
    res = '<a class=\"wiki-link'
    if missing:
        res += ' missing'
    url = urllib.parse.quote(url)
    res += '\" data-wiki-url=\"' + url + '\"'
    if mod:
        res += ' data-wiki-mod=\"' + mod + '\"'
    res += ' href="/read' + url + '"'
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
