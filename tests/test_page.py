from tests import WikkedTest, format_link, format_include
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
        self.assertEqual('A page with simple meta.\n\n', page.text)
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
        self.assertEqual('A page with a custom title.\n', page.text)
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

    def testPageInclude(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: trans-desc}}\n",
            'Trans Desc.txt': "BLAH\n"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual({'include': ['trans-desc']}, foo._getLocalMeta())
        self.assertEqual(
                "A test page.\n%s" % format_include('trans-desc'),
                foo._getFormattedText())
        self.assertEqual("A test page.\nBLAH\n\n", foo.text)

    def testPageIncludeWithMeta(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: trans-desc}}\n",
            'Trans Desc.txt': "BLAH: [[Somewhere]]\n{{bar: 42}}\n{{__secret: love}}\n{{+given: hope}}"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual([], foo._getLocalLinks())
        self.assertEqual({'include': ['trans-desc']}, foo._getLocalMeta())
        self.assertEqual(
                "A test page.\n%s" % format_include('trans-desc'),
                foo._getFormattedText())
        self.assertEqual(
                "A test page.\nBLAH: %s\n\n\n\n" % format_link('Somewhere', 'somewhere', True),
                foo.text)
        self.assertEqual(['somewhere'], foo.links)
        self.assertEqual({'bar': ['42'], 'given': ['hope'], 'include': ['trans-desc']}, foo.meta)

    def testPageIncludeWithTemplating(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: greeting|name=Dave|what=drink}}\n",
            'Greeting.txt': "Hello {{name}}, would you like a {{what}}?"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(
            "A test page.\n%s" % format_include('greeting', 'name=Dave|what=drink'),
            foo._getFormattedText())
        self.assertEqual("A test page.\nHello Dave, would you like a drink?\n", foo.text)

    def testGivenOnlyInclude(self):
        self.wiki = self._getWikiFromStructure({
            'Base.txt': "The base page.\n{{include: Template 1}}",
            'Template 1.txt': "TEMPLATE!\n{{+include: Template 2}}",
            'Template 2.txt': "MORE TEMPLATE!"
            })
        tpl1 = Page(self.wiki, 'template-1')
        self.assertEqual(
                "TEMPLATE!\n%s" % format_include('template-2', mod='+'),
                tpl1._getFormattedText())
        self.assertEqual("TEMPLATE!\n\n", tpl1.text)
        base = Page(self.wiki, 'base')
        self.assertEqual("The base page.\nTEMPLATE!\nMORE TEMPLATE!\n\n", base.text)

    def testDoublePageIncludeWithMeta(self):
        return
        self.wiki = self._getWikiFromStructure({
            'Base.txt': "The base page.\n{{include: Template 1}}",
            'Wrong.txt': "{{include: Template 2}}",
            'Template 1.txt': "{{foo: bar}}\n{{+category: blah}}\n{{+include: Template 2}}\n{{__secret1: ssh}}",
            'Template 2.txt': "{{+category: yolo}}",
            'Query 1.txt': "{{query: category=yolo}}",
            'Query 2.txt': "{{query: category=blah}}"
            })
        base = Page(self.wiki, 'base')
        self.assertEqual({
            'foo': ['bar'], 
            'category': ['blah', 'yolo']
            }, base.meta)
        tpl1 = Page(self.wiki, 'template-1')
        self.assertEqual({
            'foo': ['bar'],
            '+category': ['blah'],
            '+include': ['template-2'],
            '__secret': ['ssh']
            }, tpl1.meta)
        self.assertEqual(
                "\n\n%s\n\n" % format_include('template-2'),
                tpl1.text)
        q1 = Page(self.wiki, 'query-1')
        self.assertEqual(
                "<ul>\n<li>%s</li>\n<li>%s</li>\n</ul>" % (format_link('Base', 'base'), format_link('Wrong', 'wrong')),
                q1.text)
        q2 = Page(self.wiki, 'query-2')
        self.assertEqual(
                "<ul>\n<li>%s</li>\n</ul>" % format_link('Base', 'base'),
                q2.text)

