from tests import WikkedTest, format_link
from wikked.page import Page


class PageTest(WikkedTest):
    def testSimplePage(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': 'A test page.'
            })
        page = Page(self.wiki, 'foo')
        self.assertEqual('foo', page.url)
        self.assertEqual('foo.txt', page.path)
        self.assertEqual('foo', page.filename)
        self.assertEqual('txt', page.extension)
        self.assertEqual('A test page.', page.raw_text)
        self.assertEqual('A test page.', page._getFormattedText())
        self.assertEqual('foo', page.title)
        self.assertEqual('A test page.', page.text)
        self.assertEqual({}, page._getLocalMeta())
        self.assertEqual([], page._getLocalLinks())

    def testPageMeta(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': "A page with simple meta.\n{{bar: baz}}\n{{is_test: }}"
            })
        page = Page(self.wiki, 'foo')
        self.assertEqual('foo', page.url)
        self.assertEqual("A page with simple meta.\n{{bar: baz}}\n{{is_test: }}", page.raw_text)
        self.assertEqual('A page with simple meta.\n\n', page._getFormattedText())
        self.assertEqual('foo', page.title)
        self.assertEqual('A page with simple meta.\n', page.text)
        self.assertEqual({'bar': ['baz'], 'is_test': True}, page._getLocalMeta())
        self.assertEqual([], page._getLocalLinks())

    def testPageTitleMeta(self):
        self.wiki = self._getWikiFromStructure({
            'test_title.txt': "A page with a custom title.\n{{title: TEST-TITLE}}"
            })
        page = Page(self.wiki, 'test_title')
        self.assertEqual('test_title', page.url)
        self.assertEqual("A page with a custom title.\n{{title: TEST-TITLE}}", page.raw_text)
        self.assertEqual('A page with a custom title.\n', page._getFormattedText())
        self.assertEqual('TEST-TITLE', page.title)
        self.assertEqual('A page with a custom title.', page.text)
        self.assertEqual({'title': ['TEST-TITLE']}, page._getLocalMeta())
        self.assertEqual([], page._getLocalLinks())

    def testPageOutLinks(self):
        self.wiki = self._getWikiFromStructure({
            'test_links.txt': "Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].",
            'sandbox.txt': "This is just a placeholder."
            })
        self.assertTrue(self.wiki.pageExists('sandbox', from_db=False))
        page = Page(self.wiki, 'test_links')
        self.assertEqual('test_links', page.url)
        self.assertEqual("Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].", page.raw_text)
        self.assertEqual(
                "Follow a link to the %s. Or to %s." % (
                    format_link('Sandbox', 'sandbox'),
                    format_link('this page', 'other-sandbox', True)),
                page.text)
        self.assertEqual(set(['sandbox', 'other-sandbox']), set(page._getLocalLinks()))

    def testPageRelativeOutLinks(self):
        self.wiki = self._getWikiFromStructure({
            'first.txt': "Go to [[First Sibling]].",
            'first-sibling.txt': "Go back to [[First]], or to [[sub_dir/Second]].",
            'sub_dir': {
                'second.txt': "Go back to [[../First]], or to [[Second Sibling]].",
                'second-sibling.txt': "Go back to [[Second]]."
                }
            })
        first = Page(self.wiki, 'first')
        self.assertEqual(['first-sibling'], first._getLocalLinks())
        first2 = Page(self.wiki, 'first-sibling')
        self.assertEqual(['first', 'sub_dir/second'], first2._getLocalLinks())
        second = Page(self.wiki, 'sub_dir/second')
        self.assertEqual(['first', 'sub_dir/second-sibling'], second._getLocalLinks())
        second2 = Page(self.wiki, 'sub_dir/second-sibling')
        self.assertEqual(['sub_dir/second'], second2._getLocalLinks())

    def testGenericUrl(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': "URL: [[url:/blah/boo/image.png]]"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual("URL: /files/blah/boo/image.png", foo._getFormattedText())

    def testUrlTemplateFunctions(self):
        self.wiki =self._getWikiFromStructure({
            'foo.txt': "Here is {{read_url(__page.url, 'FOO')}}!"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(
            'Here is <a class="wiki-link" data-wiki-url="foo">FOO</a>!',
            foo.text
            )
