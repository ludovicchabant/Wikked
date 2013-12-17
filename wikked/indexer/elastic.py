import os.path
import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk_index
from wikked.indexer.base import HitResult, WikiIndex


INDEX_VERSION = 1


logger = logging.getLogger(__name__)


class ElasticWikiIndex(WikiIndex):
    def __init__(self):
        pass

    def initIndex(self, wiki):
        self.es = Elasticsearch()
        if not self.es.indices.exists('pages'):
            logger.debug("Creating the `pages` index.")
            self.es.indices.create('pages')

    def reset(self, pages):
        logger.debug("Reseting the ElasticSearch index.")
        self.es.indices.delete('pages')
        self.es.indices.create(
                'pages',
                body={
                    'mappings': {
                        'page': {
                            'properties': {
                                'url': {'type': 'string', 'index': 'not_analyzed'},
                                'path': {'type': 'string', 'index': 'not_analyzed'},
                                'time': {'type': 'float', 'index': 'not_analyzed'},
                                'title': {'type': 'string', 'boost': 2.0},
                                'text': {'type': 'string', 'index': 'analyzed', 'store': 'yes', 'analyzer': 'pageTextAnalyzer'}
                                },
                            '_meta': {
                                'version': INDEX_VERSION
                                }
                            }
                        }
                    })

        def action_maker():
            for p in pages:
                logger.debug("Indexing '%s'..." % p.url)
                a = {
                        '_index': 'pages',
                        '_type': 'page',
                        '_source': self._get_body(p)
                        }
                yield a

        actions = action_maker()
        bulk_index(self.es, actions)

    def update(self, pages):
        to_reindex = set()
        already_indexed = set()

        offset = 0
        bucket_size = 100
        while True:
            logger.debug("Grabbing documents %d to %d..." % (offset, offset + bucket_size))
            body = {
                    'fields': ['url', 'path', 'time'],
                    'from': offset,
                    'size': bucket_size,
                    'query': {
                        'match_all': {}
                        }
                    }
            docs = self.es.search(
                    index='pages',
                    doc_type='page',
                    body=body)
            total = docs['hits']['total']

            for d in docs['hits']['hits']:
                indexed_path = d['fields']['path']
                indexed_time = d['fields']['time']

                if not os.path.isfile(indexed_path):
                    # File was deleted.
                    self.es.delete(
                            index='pages',
                            doc_type='page',
                            id=d['_id'])
                else:
                    already_indexed.add(indexed_path)
                    if os.path.getmtime(indexed_path) > indexed_time:
                        # File has changed since last index.
                        to_reindex.add(indexed_path)

            if offset + bucket_size < total:
                offset += bucket_size
            else:
                break

        def action_maker():
            for p in pages:
                if p.path in to_reindex or p.path not in already_indexed:
                    logger.debug("Reindexing '%s'..." % p.url)
                    a = {
                            '_index': 'pages',
                            '_type': 'page',
                            '_source': self._get_body(p)
                            }
                    yield a

        logger.debug("Indexing out-of-date pages...")
        actions = action_maker()
        bulk_index(self.es, actions)

    def search(self, query):
        body = {
                'query': {
                    'match': {'text': query}
                    },
                'highlight': {
                    'tags_schema': 'styled',
                    'fragment_size': 150,
                    'fields': {
                        'title': {'number_of_fragments': 0},
                        'text': {'number_of_fragments': 5, 'order': 'score'}
                        }
                    }
                }
        res = self.es.search(
                index='pages',
                doc_type='page',
                body=body)
        logger.debug("Got %d hits." % res['hits']['total'])
        for h in res['hits']['hits']:
            yield HitResult(h['_source']['url'], h['_source']['title'], h['highlight']['text'])

    def _get_body(self, page):
        return {
                'url': page.url,
                'path': page.path,
                'time': os.path.getmtime(page.path),
                'title': page.title,
                'text': page.text
                }

