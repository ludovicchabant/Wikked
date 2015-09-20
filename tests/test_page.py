from tests import WikkedTest, format_link


class PageTest(WikkedTest):
    def _onWikiStarted(self, wiki):
        wiki.reset()

    def _getParameters(self, root=None):
        params = WikkedTest._getParameters(self, root)
        return params

    def testSimplePage(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': 'A test page.'
            })
        page = wiki.getPage('/foo')
        self.assertEqual('/foo', page.url)
        self.assertEqual('/foo.txt', page.path)
        self.assertEqual('foo', page.filename)
        self.assertEqual('txt', page.extension)
        self.assertEqual('A test page.', page.raw_text)
        self.assertEqual('A test page.', page.getFormattedText())
        self.assertEqual('foo', page.title)
        self.assertEqual('A test page.', page.text)
        self.assertEqual({}, page.getLocalMeta())
        self.assertEqual([], page.getLocalLinks())

    def testPageMeta(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': "A page with simple meta.\n{{bar: baz}}\n{{is_test: }}"
            })
        page = wiki.getPage('/foo')
        self.assertEqual('/foo', page.url)
        self.assertEqual("A page with simple meta.\n{{bar: baz}}\n{{is_test: }}", page.raw_text)
        self.assertEqual('A page with simple meta.\n\n', page.getFormattedText())
        self.assertEqual('foo', page.title)
        self.assertEqual('A page with simple meta.\n', page.text)
        self.assertEqual({'bar': ['baz'], 'is_test': [True]}, page.getLocalMeta())
        self.assertEqual([], page.getLocalLinks())

    def testPageTitleMeta(self):
        wiki = self._getWikiFromStructure({
            '/test_title.txt': "A page with a custom title.\n{{title: TEST-TITLE}}"
            })
        page = wiki.getPage('/test_title')
        self.assertEqual('/test_title', page.url)
        self.assertEqual("A page with a custom title.\n{{title: TEST-TITLE}}", page.raw_text)
        self.assertEqual('A page with a custom title.\n', page.getFormattedText())
        self.assertEqual('TEST-TITLE', page.title)
        self.assertEqual('A page with a custom title.', page.text)
        self.assertEqual({'title': ['TEST-TITLE']}, page.getLocalMeta())
        self.assertEqual([], page.getLocalLinks())

    def testPageOutLinks(self):
        wiki = self._getWikiFromStructure({
            '/TestLinks.txt': "Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].",
            '/Sandbox.txt': "This is just a placeholder."
            })
        self.assertTrue(wiki.pageExists('/Sandbox'))
        page = wiki.getPage('/TestLinks')
        self.assertEqual('/TestLinks', page.url)
        self.assertEqual("Follow a link to the [[Sandbox]]. Or to [[this page|Other Sandbox]].", page.raw_text)
        self.assertEqual(
                "Follow a link to the %s. Or to %s." % (
                    format_link('Sandbox', '/Sandbox'),
                    format_link('this page', '/Other Sandbox', missing=True)),
                page.text)
        self.assertEqual(set(['Sandbox', 'Other Sandbox']), set(page.getLocalLinks()))
        self.assertEqual(set(['/Sandbox', '/Other Sandbox']), set(page.links))

    def testPageRelativeOutLinks(self):
        wiki = self._getWikiFromStructure({
            '/First.txt': "Go to [[First Sibling]].",
            '/First Sibling.txt': "Go back to [[First]], or to [[sub_dir/Second]].",
            '/sub_dir/Second.txt': "Go back to [[../First]], or to [[Second Sibling]].",
            '/sub_dir/Second Sibling.txt': "Go back to [[Second]]."
            })
        first = wiki.getPage('/First')
        self.assertEqual(['/First Sibling'], first.links)
        first2 = wiki.getPage('/First Sibling')
        self.assertEqual(['/First', '/sub_dir/Second'], first2.links)
        second = wiki.getPage('/sub_dir/Second')
        self.assertEqual(['/First', '/sub_dir/Second Sibling'], second.links)
        second2 = wiki.getPage('/sub_dir/Second Sibling')
        self.assertEqual(['/sub_dir/Second'], second2.links)

    def testGenericUrl(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': "URL: [[url:/blah/boo/raw.txt]]"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual("URL: /files/blah/boo/raw.txt", foo.getFormattedText())

    def testImageUrl(self):
        wiki = self._getWikiFromStructure({
            '/foo.txt': "URL: [[blah|asset:/blah/boo/image.png]]"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual("URL: <img class=\"wiki-asset\" src=\"/files/blah/boo/image.png\" alt=\"blah\"></img>", foo.getFormattedText())

    def testUrlTemplateFunctions(self):
        wiki =self._getWikiFromStructure({
            '/foo.txt': "Here is {{read_url(__page.url, 'FOO')}}!"
            })
        foo = wiki.getPage('/foo')
        self.assertEqual(
            'Here is <a class="wiki-link" data-wiki-url="/foo" href="/read/foo">FOO</a>!',
            foo.text
            )
