import os.path
import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk_index
from wikked.indexer.base import HitResult, WikiIndex


INDEX_VERSION = 1


logger = logging.getLogger(__name__)


class ElasticWikiIndex(WikiIndex):
    def __init__(self):
        WikiIndex.__init__(self)

    def start(self, wiki):
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
                    'settings': {
                        'analysis': {
                            'analyzer': {
                                'pageTitlePreviewAnalyzer': {
                                    'type': 'custom',
                                    'tokenizer': 'standard',
                                    'filter': ['pageTitlePreviewFilter', 'lowercase']
                                    },
                                'pageTextAnalyzer': {
                                    'type': 'custom',
                                    'tokenizer': 'standard',
                                    'filter': ['standard', 'lowercase', 'stop'],
                                    'char_filter': 'html_strip'
                                    }
                                },
                            'filter': {
                                'pageTitlePreviewFilter': {
                                    'type': 'edgeNGram',
                                    'min_gram': 1,
                                    'max_gram': 10,
                                    'token_chars': ['letter', 'digit']
                                    }
                                }
                            }
                        },
                    'mappings': {
                        'page': {
                            'properties': {
                                'url': {'type': 'string', 'index': 'not_analyzed'},
                                'path': {'type': 'string', 'index': 'not_analyzed'},
                                'time': {'type': 'float', 'index': 'not_analyzed'},
                                'title_preview': {
                                    'type': 'string',
                                    'index': 'analyzed',
                                    'analyzer': 'pageTitlePreviewAnalyzer'
                                    },
                                'title': {
                                    'type': 'string',
                                    'boost': 4.0,
                                    'store': 'yes'
                                    },
                                'text': {
                                    'type': 'string',
                                    'index': 'analyzed',
                                    'store': 'yes',
                                    'analyzer': 'pageTextAnalyzer'
                                    }
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

    def updatePage(self, page):
        body = {
                'fields': ['url'],
                'query': {'term': {'url': page.url}}}
        docs = self.es.search(index='pages', doc_type='page', body=body)
        docs = list(docs)
        if len(docs) > 0:
            self.es.delete(index='pages', doc_type='page', id=docs[0]['_id'])
        self.es.index(index='page', doc_type='page', body=self._get_body(page))

    def updateAll(self, pages):
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

    def previewSearch(self, query):
        body = {
                'explain': True,
                'fields': ['title_preview', 'url'],
                'query': {
                    'query_string': {
                        'fields': ['title_preview'],
                        'default_operator': 'AND',
                        'query': query
                        }
                    },
                'highlight': {
                    'tags_schema': 'styled',
                    'order': 'score',
                    'fields': {
                        'title_preview': {'number_of_fragments': 2}
                        }
                    }
                }
        res = self.es.search(
                index='pages',
                doc_type='page',
                body=body)
        for h in res['hits']['hits']:
            yield HitResult(h['fields']['url'], h['highlight']['title_preview'])

    def search(self, query, highlight=False):
        body = {
                'fields': ['url', 'title', 'text'],
                'query': {
                    'query_string': {
                        'fields': ['title', 'text'],
                        'default_operator': 'AND',
                        'query': query
                        }
                    },
                'highlight': {
                    'tags_schema': 'styled',
                    'order': 'score',
                    'fragment_size': 150,
                    'fields': {
                        'title': {'number_of_fragments': 2},
                        'text': {'number_of_fragments': 5}
                        }
                    }
                }
        res = self.es.search(
                index='pages',
                doc_type='page',
                body=body)
        for h in res['hits']['hits']:
            yield HitResult(h['fields']['url'],
                            h['fields']['title'],
                            h['highlight']['text'])

    def _get_body(self, page):
        return {
                'url': page.url,
                'path': page.path,
                'time': os.path.getmtime(page.path),
                'title_preview': page.title,
                'title': page.title,
                'text': page.text
                }

