import os.path
import logging
import datetime
import threading
import jinja2
from queue import Queue, Empty
from repoze.lru import LRUCache
from wikked.resolver import PageResolver, ResolveOutput, CircularIncludeError


logger = logging.getLogger(__name__)


class ResolveScheduler(object):
    """ A class that can resolve multiple pages in a potentially
        multi-threaded way.
    """
    PAGE_REGISTRY_SIZE = 256

    def __init__(self, wiki, page_urls, registry_size=None):
        self.wiki = wiki
        self.page_urls = page_urls

        self._cache = LRUCache(registry_size or self.PAGE_REGISTRY_SIZE)
        self._pages_meta = None

        self._queue = None
        self._results = None
        self._pool = None
        self._done = False

    def getPage(self, url):
        page = self._cache.get(url)
        if page is None:
            logger.debug("Caching page in scheduler registry: %s" % url)
            fields = ['url', 'title', 'path', 'formatted_text', 'local_meta',
                      'local_links']
            page = self.wiki.db.getPage(url, fields=fields)
            self._cache.put(url, page)
        return page

    def getPagesMeta(self):
        if self._pages_meta is None:
            fields = ['url', 'title', 'local_meta']
            self._pages_meta = list(self.wiki.db.getPages(fields=fields))
        return self._pages_meta

    def run(self, num_workers=1):
        logger.info("Running resolve scheduler (%d workers)" % num_workers)

        if num_workers > 1:
            # Multi-threaded resolving.
            logger.debug("Main thread is %d" % threading.get_ident())

            self._done = False
            self._queue = Queue()
            self._results = Queue()

            self.getPagesMeta()

            job_count = 0
            for url in self.page_urls:
                self._queue.put_nowait(JobDesc(url))
                job_count += 1

            self._pool = []
            for i in range(num_workers):
                ctx = JobContext(self)
                self._pool.append(JobWorker(i, ctx))

            for thread in self._pool:
                thread.start()

            while job_count > 0:
                try:
                    url, page, exc = self._results.get(True, 10)
                except Empty:
                    logger.error("Resolve workers timed out, still have %d "
                                 "jobs to go." % job_count)
                    return

                job_count -= 1
                if page:
                    self.wiki.db.cachePage(page)
                if exc:
                    logger.error("Error resolving page: %s" % url)
                    logger.exception(exc)

            logger.debug("Queue is empty... terminating workers.")
            self._done = True

            for thread in self._pool:
                thread.join()
                logger.debug("Worker [%d] ended." % thread.wid)
        else:
            # Single-threaded resolving.
            for url in self.page_urls:
                page = self.getPage(url)
                r = PageResolver(
                        page,
                        page_getter=self.getPage,
                        pages_meta_getter=self.getPagesMeta)
                runner = PageResolverRunner(page, r)
                runner.run(raise_on_failure=True)
                self.wiki.db.cachePage(page)


class PageResolverRunner(object):
    """ A class that resolves one page with the option to fail hard or
        softly (i.e. raise an exception, or replace the page's text with
        the error message).
    """
    def __init__(self, page, resolver):
        self.page = page
        self.resolver = resolver

    def run(self, raise_on_failure=False):
        try:
            logger.debug("Resolving page: %s" % self.page.url)
            result = self.resolver.run()
        except CircularIncludeError as cie:
            if raise_on_failure:
                raise

            # Handle error by printing it in the page's text so the
            # user can see it.
            template_path = os.path.join(
                os.path.dirname(__file__),
                'templates',
                'circular_include_error.html')
            with open(template_path, 'r') as f:
                env = jinja2.Environment()
                template = env.from_string(f.read())

            result = ResolveOutput()
            result.text = template.render({
                    'message': str(cie),
                    'url_trail': cie.url_trail})

        self.page._setExtendedData(result)


class JobDesc(object):
    def __init__(self, url):
        self.url = url


class JobContext(object):
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.abort_on_failure = True

    def isDone(self):
        return self.scheduler._done

    def getJob(self):
        return self.scheduler._queue.get(True, 0.5)

    def sendResult(self, url, page, exception):
        res = (url, page, exception)
        self.scheduler._results.put_nowait(res)
        self.scheduler._queue.task_done()


class JobWorker(threading.Thread):
    def __init__(self, wid, ctx):
        super(JobWorker, self).__init__(daemon=True)
        self.wid = wid
        self.ctx = ctx

    def run(self):
        logger.debug("Starting worker on thread %d" % threading.get_ident())
        try:
            self._unsafeRun()
        except Exception as ex:
            logger.exception(ex)
            logger.critical("Aborting resolver worker.")

    def _unsafeRun(self):
        while True:
            try:
                job = self.ctx.getJob()
            except Empty:
                if self.ctx.isDone():
                    break
                continue
            logger.debug("[%d] -> %s" % (self.wid, job.url))
            before = datetime.datetime.now()

            try:
                page = self.ctx.scheduler.getPage(job.url)
                r = PageResolver(
                        page,
                        page_getter=self.ctx.scheduler.getPage,
                        pages_meta_getter=self.ctx.scheduler.getPagesMeta)
                runner = PageResolverRunner(page, r)
                runner.run(raise_on_failure=self.ctx.abort_on_failure)
                self.ctx.sendResult(job.url, page, None)
            except Exception as ex:
                logger.exception(ex)
                logger.error("Error resolving page: %s" % job.url)
                self.ctx.sendResult(job.url, None, ex)
                return

            after = datetime.datetime.now()
            delta = after - before
            logger.debug("[%d] %s done in %fs" % (
                    self.wid, job.url, delta.total_seconds()))

