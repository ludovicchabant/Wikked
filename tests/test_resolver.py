# flake8: noqa
from tests import WikkedTest, format_link, format_include


class ResolverTest(WikkedTest):
    def testPageInclude(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': "A test page.\n{{include: trans-desc}}\n",
            '/trans-desc.txt': "BLAH\n"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual({'include': ['trans-desc']}, foo.getLocalMeta())
        self.assertEqual(
                "A test page.\n%s" % format_include('trans-desc'),
                foo.getFormattedText())
        self.assertEqual("A test page.\nBLAH", foo.text)

    def testPageIncludeWithMeta(self):
        wiki = self._getWikiFromStructure({
            'foo.txt': "A test page.\n{{include: trans-desc}}\n",
            'trans-desc.txt': "BLAH: [[Somewhere]]\n{{bar: 42}}\n{{__secret: love}}\n{{+given: hope}}"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual([], foo.getLocalLinks())
        self.assertEqual({'include': ['trans-desc']}, foo.getLocalMeta())
        self.assertEqual(
                "A test page.\n%s" % format_include('trans-desc'),
                foo.getFormattedText())
        self.assertEqual(
                "A test page.\nBLAH: %s\n\n" % format_link('Somewhere', '/Somewhere', True),
                foo.text)
        self.assertEqual(['/Somewhere'], foo.links)
        self.assertEqual({'bar': ['42'], 'given': ['hope'], 'include': ['trans-desc']}, foo.getMeta())

    def testPageIncludeWithNamedTemplating(self):
        wiki = self._getWikiFromStructure({
            'foo.txt': "A test page.\n{{include: greeting|name=Dave|what=drink}}\n",
            'greeting.txt': "Hello {{name}}, would you like a {{what}}?"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual(
            "A test page.\n%s" % format_include(
                'greeting',
                '<div class="wiki-param" data-name="name">Dave</div><div class="wiki-param" data-name="what">drink</div>'),
            foo.getFormattedText())
        self.assertEqual("A test page.\nHello Dave, would you like a drink?", foo.text)

    def testPageIncludeWithNumberedTemplating(self):
        wiki = self._getWikiFromStructure({
            'foo.txt': "A test page.\n{{include: greeting|Dave|Roger|Tom}}\n",
            'greeting.txt': "Hello {{__args[0]}}, {{__args[1]}} and {{__args[2]}}."
            })
        foo = wiki.getPage('/foo')
        self.assertEqual(
            "A test page.\n%s" % format_include(
                'greeting',
                '<div class="wiki-param" data-name="">Dave</div><div class="wiki-param" data-name="">Roger</div><div class="wiki-param" data-name="">Tom</div>'),
            foo.getFormattedText())
        self.assertEqual("A test page.\nHello Dave, Roger and Tom.", foo.text)

    def testIncludeWithPageReferenceTemplating(self):
        wiki =self._getWikiFromStructure({
            'selfref.txt': "Here is {{read_url(__page.url, __page.title)}}!",
            'foo.txt': "Hello here.\n{{include: selfref}}\n"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual(
            'Hello here.\nHere is <a class="wiki-link" data-wiki-url="/foo" href="/read/foo">foo</a>!',
            foo.text
            )

    def testGivenOnlyInclude(self):
        wiki = self._getWikiFromStructure({
            'Base.txt': "The base page.\n{{include: Template 1}}",
            'Template 1.txt': "TEMPLATE!\n{{+include: Template 2}}",
            'Template 2.txt': "MORE TEMPLATE!"
            })
        tpl1 = wiki.getPage('/Template 1')
        self.assertEqual(
                "TEMPLATE!\n%s" % format_include('Template 2', mod='+'),
                tpl1.getFormattedText())
        self.assertEqual("TEMPLATE!\n", tpl1.text)
        base = wiki.getPage('/Base')
        self.assertEqual("The base page.\nTEMPLATE!\nMORE TEMPLATE!", base.text)

    def testDoublePageIncludeWithMeta(self):
        wiki = self._getWikiFromStructure({
            'Base.txt': "The base page.\n{{include: Template 1}}",
            'Other.txt': "The other page.\n{{include: Template 2}}",
            'Template 1.txt': "{{foo: bar}}\n{{+category: blah}}\n{{+include: Template 2}}\n{{__secret1: ssh}}",
            'Template 2.txt': "{{+category: yolo}}",
            'Query 1.txt': "{{query: category=yolo}}",
            'Query 2.txt': "{{query: category=blah}}"
            })

        base = wiki.getPage('/Base')
        self.assertEqual({
            'foo': ['bar'],
            'category': ['blah', 'yolo'],
            'include': ['Template 1', 'Template 2']
            }, base.getMeta())

        other = wiki.getPage('/Other')
        self.assertEqual({
            'category': ['yolo'],
            'include': ['Template 2']
        }, other.getMeta())

        tpl1 = wiki.getPage('/Template 1')
        self.assertEqual({
            'foo': ['bar'],
            '+category': ['blah', 'yolo'],
            '+include': ['Template 2'],
            '__secret1': ['ssh']
            }, tpl1.getMeta())

        self.assertEqual(
                "\n\n\n", #"\n\n%s\n\n" % format_include('/Template 2'),
                tpl1.text)
        q1 = wiki.getPage('/Query 1')
        self.assertEqual(
                "\n* %s\n* %s\n\n" % (format_link('Base', '/Base'), format_link('Other', '/Other')),
                q1.text)
        q2 = wiki.getPage('/Query 2')
        self.assertEqual(
                "\n* %s\n\n" % format_link('Base', '/Base'),
                q2.text)

    def testLink1(self):
        wiki = self._getWikiFromStructure({
            'Source.txt': "A link: [[Other]]",
            'Other.txt': ""
        })

        source = wiki.getPage('/Source')
        self.assertEqual("A link: %s" % format_link('Other', '/Other'),
                         source.text)

    def testLink2(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "A link: [[Other]]",
            'Folder/Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual("A link: %s" % format_link('Other', '/Folder/Other'),
                         source.text)

    def testLink3(self):
        wiki = self._getWikiFromStructure({
            'Source.txt': "[[Folder/Other]]",
            'Folder/Other.txt': ""
        })

        source = wiki.getPage('/Source')
        self.assertEqual(format_link('Other', '/Folder/Other'),
                         source.text)

    def testLink4(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "[[More/Other]]",
            'Folder/More/Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/More/Other'),
                         source.text)

    def testRelativeLink1(self):
        wiki = self._getWikiFromStructure({
            'Source.txt': "[[./Other]]",
            'Source/Other.txt': ""
        })

        source = wiki.getPage('/Source')
        self.assertEqual(format_link('Other', '/Source/Other'),
                         source.text)

    def testRelativeLink2(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "[[./Other]]",
            'Folder/Source/Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/Source/Other'),
                         source.text)

    def testRelativeLink3(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "[[../Other]]",
            'Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual(format_link('Other', '/Other'), source.text)

    def testRelativeLink4(self):
        wiki = self._getWikiFromStructure({
            'Folder/More/Source.txt': "[[../Other]]",
            'Folder/Other.txt': ""
        })

        source = wiki.getPage('/Folder/More/Source')
        self.assertEqual(format_link('Other', '/Folder/Other'), source.text)

    def testEndpointLink1(self):
        wiki = self._getWikiFromStructure({
            'Source.txt': "[[blah:Other]]",
            '_meta/blah/Other.txt': ""
        })

        source = wiki.getPage('/Source')
        self.assertEqual(format_link('Other', '/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink2(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "[[blah:/Other]]",
            '_meta/blah/Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual(format_link('Other', '/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink3(self):
        wiki = self._getWikiFromStructure({
            'Source.txt': "[[blah:/Folder/Other]]",
            '_meta/blah/Folder/Other.txt': ""
        })

        source = wiki.getPage('/Source')
        self.assertEqual(format_link('Other', '/Folder/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink4(self):
        wiki = self._getWikiFromStructure({
            'Folder/Source.txt': "[[blah:Other]]",
            '_meta/blah/Folder/Other.txt': ""
        })

        source = wiki.getPage('/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink5(self):
        wiki = self._getWikiFromStructure({
            '_meta/foo/Folder/Source.txt': "[[blah:Other]]",
            '_meta/blah/Folder/Other.txt': ""
        })

        source = wiki.getPage('foo:/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink6(self):
        wiki = self._getWikiFromStructure({
            '_meta/blah/Folder/Source.txt': "[[Other]]",
            '_meta/blah/Folder/Other.txt': ""
        })

        source = wiki.getPage('blah:/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink7(self):
        wiki = self._getWikiFromStructure({
            '_meta/blah/Source.txt': "[[Folder/Other]]",
            '_meta/blah/Folder/Other.txt': ""
        })

        source = wiki.getPage('blah:/Source')
        self.assertEqual(format_link('Other', '/Folder/Other', endpoint='blah'),
                         source.text)

    def testEndpointLink8(self):
        wiki = self._getWikiFromStructure({
            '_meta/blah/Source.txt': "[[:/Other]]",
            'Other.txt': ""
        })

        source = wiki.getPage('blah:/Source')
        self.assertEqual(format_link('Other', '/Other'), source.text)

    def testEndpointLink9(self):
        wiki = self._getWikiFromStructure({
            '_meta/blah/Folder/Source.txt': "[[:Other]]",
            'Folder/Other.txt': ""
        })

        source = wiki.getPage('blah:/Folder/Source')
        self.assertEqual(format_link('Other', '/Folder/Other'), source.text)
