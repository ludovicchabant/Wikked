import os
import os.path
import logging
from .base import WikiIndex, HitResult
from whoosh.analysis import (StandardAnalyzer, StemmingAnalyzer,
        CharsetFilter, NgramFilter)
from whoosh.fields import Schema, ID, TEXT, STORED
from whoosh.highlight import WholeFragmenter, UppercaseFormatter
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser
from whoosh.support.charset import accent_map


logger = logging.getLogger(__name__)


class WhooshWikiIndex(WikiIndex):
    def __init__(self):
        WikiIndex.__init__(self)

    def start(self, wiki):
        self.store_dir = os.path.join(wiki.root, '.wiki', 'index')
        if not os.path.isdir(self.store_dir):
            logger.debug("Creating new index in: " + self.store_dir)
            os.makedirs(self.store_dir)
            self.ix = create_in(self.store_dir, self._getSchema())
        else:
            self.ix = open_dir(self.store_dir)

    def reset(self, pages):
        logger.info("Re-creating new index in: " + self.store_dir)
        self.ix = create_in(self.store_dir, schema=self._getSchema())
        writer = self.ix.writer()
        for page in pages:
            self._indexPage(writer, page)
        writer.commit()

    def updatePage(self, page):
        logger.info("Updating index for page: %s" % page.url)
        writer = self.ix.writer()
        self._unindexPage(writer, page.url)
        self._indexPage(writer, page)
        writer.commit()

    def updateAll(self, pages):
        logger.info("Updating index...")
        to_reindex = set()
        already_indexed = set()

        with self.ix.searcher() as searcher:
            writer = self.ix.writer()

            for fields in searcher.all_stored_fields():
                indexed_url = fields['url']
                indexed_path = fields['path']
                indexed_time = fields['time']

                if not os.path.isfile(indexed_path):
                    # File was deleted.
                    self._unindexPage(writer, indexed_url)
                else:
                    already_indexed.add(indexed_path)
                    if os.path.getmtime(indexed_path) > indexed_time:
                        # File has changed since last index.
                        self._unindexPage(writer, indexed_url)
                        to_reindex.add(indexed_path)

            for page in pages:
                if page.path in to_reindex or page.path not in already_indexed:
                    self._indexPage(writer, page)

            writer.commit()
        logger.debug("...done updating index.")

    def previewSearch(self, query):
        with self.ix.searcher() as searcher:
            title_qp = QueryParser("title_preview", self.ix.schema).parse(query)
            results = searcher.search(title_qp)
            results.fragmenter = WholeFragmenter()

            hits = []
            for result in results:
                hit = HitResult(
                        result['url'],
                        result.highlights('title_preview', text=result['title']))
                hits.append(hit)
            return hits

    def search(self, query, highlight=True):
        with self.ix.searcher() as searcher:
            title_qp = QueryParser("title", self.ix.schema).parse(query)
            text_qp = QueryParser("text", self.ix.schema).parse(query)
            comp_query = title_qp | text_qp
            results = searcher.search(comp_query)
            if not highlight:
                results.formatter = UppercaseFormatter()

            hits = []
            for result in results:
                hit = HitResult(
                        result['url'],
                        result.highlights('title'),
                        result.highlights('text'))
                hits.append(hit)
            return hits

    def _getSchema(self):
        preview_analyzer = (StandardAnalyzer() | CharsetFilter(accent_map) |
                NgramFilter(minsize=1))
        text_analyzer = StemmingAnalyzer() | CharsetFilter(accent_map)
        schema = Schema(
                url=ID(stored=True),
                title_preview=TEXT(analyzer=preview_analyzer, stored=False),
                title=TEXT(analyzer=text_analyzer, stored=True),
                text=TEXT(analyzer=text_analyzer, stored=True),
                path=STORED,
                time=STORED
                )
        return schema

    def _indexPage(self, writer, page):
        logger.debug("Indexing '%s'." % page.url)
        writer.add_document(
            url=page.url,
            title_preview=page.title,
            title=page.title,
            text=page.text,
            path=page.path,
            time=os.path.getmtime(page.path)
            )

    def _unindexPage(self, writer, url):
        logger.debug("Removing '%s' from index." % url)
        writer.delete_by_term('url', url)

