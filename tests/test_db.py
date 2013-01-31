import os.path
from tests import WikkedTest
from mock import MockFileSystem
from wikked.fs import FileSystem
from wikked.db import SQLiteDatabase


class DatabaseTest(WikkedTest):
    def tearDown(self):
        if hasattr(self, 'wiki') and self.wiki:
            self.wiki.db.close()
        WikkedTest.tearDown(self)

    def testEmpty(self):
        self.wiki = self._getWikiFromStructure({})
        self.assertEqual([], list(self.wiki.getPageUrls()))

    def testOnePage(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': 'A test page.'
            })
        self.assertEqual(['foo'], list(self.wiki.getPageUrls()))
        page = self.wiki.getPage('foo')
        self.assertEqual('foo', page.url)
        self.assertEqual(os.path.join(self.root, 'foo.txt'), page.path)
        self.assertEqual('A test page.', page.raw_text)

    def _getWikiFromStructure(self, structure):
        MockFileSystem.save_structure(self.root, structure)
        wiki = self.getWiki(
            db_factory=self._dbFactory,
            fs_factory=self._fsFactory
            )

        # Open the DB before we do anything so that it will be closed
        # only on `tearDown` (memory DBs are discarded when the
        # connection is closed.
        wiki.db.open()

        wiki.start()
        return wiki

    def _fsFactory(self, config):
        return FileSystem(self.root)

    def _dbFactory(self, config):
        return SQLiteDatabase(':memory:')
