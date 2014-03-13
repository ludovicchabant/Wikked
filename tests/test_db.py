from tests import WikkedTest


class DatabaseTest(WikkedTest):
    def testEmpty(self):
        wiki = self._getWikiFromStructure({})
        self.assertEqual([], list(wiki.getPageUrls()))

    def testOnePage(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': 'A test page.'
            })
        self.assertEqual(['/foo'], list(wiki.getPageUrls()))
        page = wiki.getPage('/foo')
        self.assertEqual('/foo', page.url)
        self.assertEqual('/foo.txt', page.path)
        self.assertEqual('A test page.', page.raw_text)
