import os
import os.path
import codecs
import logging
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, ID, TEXT, STORED
from whoosh.qparser import QueryParser


class WikiIndex(object):
    def __init__(self, store_dir, logger=None):
        self.store_dir = store_dir
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.index')

    def initIndex(self):
        raise NotImplementedError()

    def reset(self, pages):
        raise NotImplementedError()

    def update(self, pages):
        raise NotImplementedError()

    def search(self, query):
        raise NotImplementedError()


class WhooshWikiIndex(WikiIndex):
    def __init__(self, store_dir, logger=None):
        WikiIndex.__init__(self, store_dir, logger)

    def initIndex(self):
        if not os.path.isdir(self.store_dir):
            self.logger.debug("Creating new index in: " + self.store_dir)
            os.makedirs(self.store_dir)
            self.ix = create_in(self.store_dir, self._getSchema())
        else:
            self.ix = open_dir(self.store_dir)

    def reset(self, pages):
        self.logger.debug("Re-creating new index in: " + self.store_dir)
        self.ix = create_in(self.store_dir, schema=self._getSchema())
        writer = self.ix.writer()
        for page in pages:
            page._ensureMeta()
            self._indexPage(writer, page)
        writer.commit()

    def update(self, pages):
        self.logger.debug("Updating index...")
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
                page._ensureMeta()
                page_path = page._meta['path']
                if page_path in to_reindex or page_path not in already_indexed:
                    self._indexPage(writer, page)

            writer.commit()
        self.logger.debug("...done updating index.")

    def search(self, query):
        with self.ix.searcher() as searcher:
            title_qp = QueryParser("title", self.ix.schema).parse(query)
            content_qp = QueryParser("content", self.ix.schema).parse(query)
            comp_query = title_qp | content_qp
            results = searcher.search(comp_query)

            page_infos = []
            for hit in results:
                page_info = {
                        'title': hit['title'],
                        'url': hit['url']
                        }
                page_info['title_highlights'] = hit.highlights('title')
                with codecs.open(hit['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                page_info['content_highlights'] = hit.highlights('content', text=content)
                page_infos.append(page_info)
            return page_infos

    def _getSchema(self):
        schema = Schema(
                url=ID(stored=True),
                title=TEXT(stored=True),
                content=TEXT,
                path=STORED,
                time=STORED
                )
        return schema

    def _indexPage(self, writer, page):
        self.logger.debug("Indexing '%s'." % page.url)
        writer.add_document(
            url=unicode(page.url),
            title=unicode(page.title),
            content=unicode(page.raw_text),
            path=page._meta['path'],
            time=os.path.getmtime(page._meta['path'])
            )

    def _unindexPage(self, writer, url):
        self.logger.debug("Removing '%s' from index." % url)
        writer.delete_by_term('url', url)
