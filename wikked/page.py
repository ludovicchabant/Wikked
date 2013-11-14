import os
import os.path
import re
import datetime
import jinja2
from formatter import PageFormatter, FormattingContext
from resolver import PageResolver, CircularIncludeError


class PageLoadingError(Exception):
    """ An exception that can get raised if a page can't be loaded.
    """
    pass


class PageData(object):
    def __init__(self):
        self.path = None
        self.title = None
        self.raw_text = None
        self.formatted_text = None
        self.text = None
        self.local_meta = {}
        self.local_links = []
        self.ext_meta = {}
        self.ext_links = []
        self.has_extended_data = False


class Page(object):
    """ A wiki page. This is a non-functional class, as it doesn't know where
        to load things from. Use `FileSystemPage` or `DatabasePage` instead.
    """
    def __init__(self, wiki, url):
        if url[0] != '/':
            raise ValueError("Page URLs need to be absolute: " + url)

        self.wiki = wiki
        self.url = url
        self._data = None
        self._force_resolve = False

    @property
    def path(self):
        self._ensureData()
        return self._data.path

    @property
    def extension(self):
        self._ensureData()
        return self._data.extension

    @property
    def filename(self):
        self._ensureData()
        return self._data.filename

    @property
    def title(self):
        self._ensureData()
        return self._data.title

    @property
    def raw_text(self):
        self._ensureData()
        return self._data.raw_text

    @property
    def text(self):
        self._ensureExtendedData()
        return self._data.text

    @property
    def meta(self):
        self._ensureExtendedData()
        return self._data.ext_meta

    @property
    def links(self):
        self._ensureExtendedData()
        return self._data.ext_links

    def getIncomingLinks(self):
        return self.wiki.db.getLinksTo(self.url)

    def getHistory(self):
        return self.wiki.scm.getHistory(self.path)

    def getState(self):
        return self.wiki.scm.getState(self.path)

    def getRevision(self, rev):
        return self.wiki.scm.getRevision(self.path, rev)

    def getDiff(self, rev1, rev2):
        return self.wiki.scm.diff(self.path, rev1, rev2)

    def getFormattedText(self):
        self._ensureData()
        return self._data.formatted_text

    def getLocalMeta(self):
        self._ensureData()
        return self._data.local_meta

    def getLocalLinks(self):
        self._ensureData()
        return self._data.local_links

    def _ensureData(self):
        if self._data is not None:
            return

        self._data = self._loadData()
        if self._data is not None:
            return

        raise PageLoadingError()

    def _loadData(self):
        raise NotImplementedError()

    def _onExtendedDataLoading(self):
        pass

    def _onExtendedDataLoaded(self):
        pass

    def _ensureExtendedData(self):
        if self._data is not None and self._data.has_extended_data:
            return
    
        self._ensureData()

        self._onExtendedDataLoading()
        if self._data.has_extended_data and not self._force_resolve:
            return
        
        try:
            r = PageResolver(self)
            out = r.run()
            self._data.text = out.text
            self._data.ext_meta = out.meta
            self._data.ext_links = out.out_links
            self._data.has_extended_data = True
            self._onExtendedDataLoaded()
        except CircularIncludeError as cie:
            template_path = os.path.join(
                    os.path.dirname(__file__),
                    'templates',
                    'circular_include_error.html'
                    )
            with open(template_path, 'r') as f:
                env = jinja2.Environment()
                template = env.from_string(f.read())
            self._data.text = template.render({
                    'message': str(cie),
                    'url_trail': cie.url_trail
                    })


class FileSystemPage(Page):
    """ A page that can load its properties directly from the file-system.
    """
    def __init__(self, wiki, url=None, page_info=None):
        if url and page_info:
            raise Exception("You can't specify both an url and a page info.")
        if not url and not page_info:
            raise Exception("You need to specify either a url or a page info.")

        super(FileSystemPage, self).__init__(wiki, url or page_info.url)
        self._page_info = page_info

    @property
    def path(self):
        if self._page_info:
            return self._page_info.path
        return super(FileSystemPage, self).path

    def _loadData(self):
        # Get info from the file-system.
        page_info = self._page_info or self.wiki.fs.getPage(self.url)
        data = self._loadFromPageInfo(page_info)
        self._page_info = None
        return data

    def _loadFromPageInfo(self, page_info):
        data = PageData()
        data.path = page_info.path
        data.raw_text = page_info.content
        split = os.path.splitext(data.path)
        data.filename = split[0]
        data.extension = split[1].lstrip('.')

        # Format the page and get the meta properties.
        filename = os.path.basename(data.path)
        filename_split = os.path.splitext(filename)
        ctx = FormattingContext(self.url)
        f = PageFormatter(self.wiki)
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        # Add some common meta.
        data.title = re.sub(r'\-', ' ', filename_split[0])
        if 'title' in data.local_meta:
            data.title = data.local_meta['title'][0]

        return data

    @staticmethod
    def fromPageInfos(wiki, page_infos):
        for p in page_infos:
            yield FileSystemPage(wiki, page_info=p)


class DatabasePage(Page):
    """ A page that can load its properties from a database.
    """
    def __init__(self, wiki, url=None, db_obj=None):
        if url and db_obj:
            raise Exception("You can't specify both an url and a database object.")
        if not url and not db_obj:
            raise Exception("You need to specify either a url or a database object.")

        super(DatabasePage, self).__init__(wiki, url or db_obj.url)
        self.auto_update = wiki.config.get('wiki', 'auto_update')
        self._db_obj = db_obj

    @property
    def path(self):
        if self._db_obj:
            return self._db_obj.path
        return super(DatabasePage, self).path

    @property
    def _id(self):
        if self._db_obj:
            return self._db_obj.id
        self._ensureData()
        return self._data._db_id

    def _loadData(self):
        db_obj = self._db_obj or self.wiki.db.getPage(self.url)
        if db_obj is None:
            raise Exception("Can't find page '%s' in the database. Please run `update` or `reset`." % self.url)
        data = self._loadFromDbObject(db_obj)
        self._db_obj = None
        return data

    def _onExtendedDataLoaded(self):
        self.wiki.db._cacheExtendedData(self)

    def _loadFromDbObject(self, db_obj, bypass_auto_update=False):
        if not bypass_auto_update and self.auto_update:
            path_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(db_obj.path))
            if path_time >= db_obj.time:
                self.wiki.logger.debug(
                    "Updating database cache for page '%s'." % self.url)
                fs_page = FileSystemPage(self.wiki, self.url)
                fs_page._ensureData()
                added_ids = self.wiki.db.update([fs_page])
                fs_page._data._db_id = added_ids[0]
                return fs_page._data

        data = PageData()
        data._db_id = db_obj.id
        data.path = db_obj.path
        split = os.path.splitext(data.path)
        data.filename = split[0]
        data.extension = split[1].lstrip('.')
        data.title = db_obj.title
        data.raw_text = db_obj.raw_text
        data.formatted_text = db_obj.formatted_text

        data.local_meta = {}
        for m in db_obj.meta:
            value = data.local_meta.get(m.name)
            if value is None:
                data.local_meta[m.name] = [m.value]
            else:
                data.local_meta[m.name].append(m.value)

        data.local_links = [l.target_url for l in db_obj.links]

        if db_obj.is_ready and not self._force_resolve:
            # If we have extended cache data from the database, we might as
            # well load it now too.
            data.text = db_obj.ready_text
            for m in db_obj.ready_meta:
                value = data.ext_meta.get(m.name)
                if value is None:
                    data.ext_meta[m.name] = [m.value]
                else:
                    data.ext_meta[m.name].append(m.value)
            data.ext_links = [l.target_url for l in db_obj.ready_links]
            # Flag this data as completely loaded.
            data.has_extended_data = True

        return data

