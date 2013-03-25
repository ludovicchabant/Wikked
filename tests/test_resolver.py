from tests import WikkedTest, format_link, format_include
from wikked.page import Page


class ResolverTest(WikkedTest):
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

    def testPageIncludeWithNamedTemplating(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: greeting|name=Dave|what=drink}}\n",
            'Greeting.txt': "Hello {{name}}, would you like a {{what}}?"
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(
            "A test page.\n%s" % format_include('greeting', 'name=Dave|what=drink'),
            foo._getFormattedText())
        self.assertEqual("A test page.\nHello Dave, would you like a drink?\n", foo.text)

    def testPageIncludeWithNumberedTemplating(self):
        self.wiki = self._getWikiFromStructure({
            'Foo.txt': "A test page.\n{{include: greeting|Dave|Roger|Tom}}\n",
            'Greeting.txt': "Hello {{1}}, {{2}} and {{3}}."
            })
        foo = Page(self.wiki, 'foo')
        self.assertEqual(
            "A test page.\n%s" % format_include('greeting', 'Dave|Roger|Tom'),
            foo._getFormattedText())
        self.assertEqual("A test page.\nHello Dave, Roger and Tom.\n", foo.text)

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

