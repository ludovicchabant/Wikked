from tests import WikkedTest
from mock import MockFileSystem
from wikked.page import Page


class PageTest(WikkedTest):
    def _getWikiFromStructure(self, structure):
        wiki = self.getWiki(use_db=False, fs_factory=lambda cfg: MockFileSystem(structure))
        wiki.start()
        return wiki

    def testSimplePage(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': 'A test page.'
            })
        page = Page(self.wiki, 'foo')
        self.assertEqual('foo', page.url)
        self.assertEqual('A test page.', page.raw_text)
        self.assertEqual('A test page.', page.formatted_text)
        self.assertEqual('foo', page.title)
        self.assertEqual('A test page.', page.text)
        self.assertEqual({}, page.local_meta)
        self.assertEqual([], page.local_links)
        self.assertEqual([], page.local_includes)

    def testPageMeta(self):
        self.wiki = self._getWikiFromStructure({
            'foo.txt': "A page with simple meta.\n{{bar: baz}}\n{{is_test: }}"
            })
        page = Page(self.wiki, 'foo')
        self.assertEqual('foo', page.url)
        self.assertEqual("A page with simple meta.\n{{bar: baz}}\n{{is_test: }}", page.raw_text)
        self.assertEqual('A page with simple meta.\n\n', page.formatted_text)
        self.assertEqual('foo', page.title)
        self.assertEqual('A page with simple meta.\n\n', page.text)
        self.assertEqual({'bar': 'baz', 'is_test': True}, page.local_meta)
        self.assertEqual([], page.local_links)
        self.assertEqual([], page.local_includes)

    def testPageTitleMeta(self):
        self.wiki = self._getWikiFromStructure({
            'test_title.txt': "A page with a custom title.\n{{title: TEST-TITLE}}"
            })
        page = Page(self.wiki, 'test_title')
        self.assertEqual('test_title', page.url)
        self.assertEqual("A page with a custom title.\n{{title: TEST-TITLE}}", page.raw_text)
        self.assertEqual('A page with a custom title.\n', page.formatted_text)
        self.assertEqual('TEST-TITLE', page.title)
        self.assertEqual('A page with a custom title.\n', page.text)
        self.assertEqual({'title': 'TEST-TITLE'}, page.local_meta)
        self.assertEqual([], page.local_links)
        self.assertEqual([], page.local_includes)

    def testPageOutLinks(self):
        self.wiki = self._getWikiFromStructure({
            'test_links.txt': "Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].",
            'sandbox.txt': "This is just a placeholder."
            })
        self.assertTrue(self.wiki.pageExists('sandbox', from_db=False))
        page = Page(self.wiki, 'test_links')
        self.assertEqual('test_links', page.url)
        self.assertEqual("Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].", page.raw_text)
        self.assertEqual("Follow a link to the <a class=\"wiki-link\" data-wiki-url=\"sandbox\">Sandbox</a>. Or to <a class=\"wiki-link missing\" data-wiki-url=\"other-sandbox\">this page</a>.", page.formatted_text)
        self.assertEqual(set(['sandbox', 'other-sandbox']), set(page.local_links))

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
        self.assertEqual(['first-sibling'], first.local_links)
        first2 = Page(self.wiki, 'first-sibling')
        self.assertEqual(['first', 'sub_dir/second'], first2.local_links)
        second = Page(self.wiki, 'sub_dir/second')
        self.assertEqual(['first', 'sub_dir/second-sibling'], second.local_links)
        second2 = Page(self.wiki, 'sub_dir/second-sibling')
        self.assertEqual(['sub_dir/second'], second2.local_links)

    def testPageInclude(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: trans-desc}}\n",
            'Trans Desc.txt': "BLAH\n"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(['trans-desc'], foo.local_includes)
        self.assertEqual("A test page.\n<div class=\"wiki-include\" data-wiki-url=\"trans-desc\"></div>\n", foo.formatted_text)
        self.assertEqual("A test page.\nBLAH\n\n", foo.text)

    def testPageIncludeWithMeta(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: trans-desc}}\n",
            'Trans Desc.txt': "BLAH: [[Somewhere]]\n{{bar: 42}}\n{{__secret: love}}\n{{+given: hope}}"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(['trans-desc'], foo.local_includes)
        self.assertEqual([], foo.local_links)
        self.assertEqual({'include': 'trans-desc'}, foo.local_meta)
        self.assertEqual("A test page.\n<div class=\"wiki-include\" data-wiki-url=\"trans-desc\"></div>\n", foo.formatted_text)
        self.assertEqual("A test page.\nBLAH: <a class=\"wiki-link missing\" data-wiki-url=\"somewhere\">Somewhere</a>\n\n\n\n", foo.text)
        self.assertEqual(['trans-desc'], foo.all_includes)
        self.assertEqual(['somewhere'], foo.all_links)
        self.assertEqual({'bar': '42', 'given': 'hope', 'include': 'trans-desc'}, foo.all_meta)

    def testPageIncludeWithTemplating(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: greeting|name=Dave|what=drink}}\n",
            'Greeting.txt': "Hello {{name}}, would you like a {{what}}?"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual("A test page.\n<div class=\"wiki-include\" data-wiki-url=\"greeting\">name=Dave|what=drink</div>\n", foo.formatted_text)
        self.assertEqual("A test page.\nHello Dave, would you like a drink?\n", foo.text)

