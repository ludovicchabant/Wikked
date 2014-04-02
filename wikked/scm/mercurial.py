import re
import os
import os.path
import time
import logging
import tempfile
import threading
import subprocess
from hglib.error import CommandError
from hglib.util import cmdbuilder
from base import (
        SourceControl, Author, Revision, SourceControlError,
        ACTION_ADD, ACTION_EDIT, ACTION_DELETE,
        STATE_NEW, STATE_MODIFIED, STATE_COMMITTED)


logger = logging.getLogger(__name__)


class MercurialBaseSourceControl(SourceControl):
    def __init__(self, root):
        SourceControl.__init__(self)
        self.root = root
        self.actions = {
                'A': ACTION_ADD,
                'R': ACTION_DELETE,
                'M': ACTION_EDIT
                }

    def start(self, wiki):
        self._doStart()

    def init(self, wiki):
        # Make a Mercurial repo if there's none.
        if not os.path.isdir(os.path.join(self.root, '.hg')):
            logger.info("Creating Mercurial repository at: " + self.root)
            self._initRepo(self.root)

        self._doStart()

        # Create a `.hgignore` file is there's none.
        ignore_path = os.path.join(self.root, '.hgignore')
        if not os.path.isfile(ignore_path):
            logger.info("Creating `.hgignore` file.")
            with open(ignore_path, 'w') as f:
                f.write('.wiki')
            self.commit([ignore_path], {'message': "Created `.hgignore`."})

    def _doStart(self):
        pass

    def getSpecialFilenames(self):
        return ['.hg*']


class MercurialSourceControl(MercurialBaseSourceControl):
    def __init__(self, root):
        MercurialBaseSourceControl.__init__(self, root)

        self.hg = 'hg'
        self.log_style = os.path.join(os.path.dirname(__file__), 'resources', 'hg_log.style')

    def getHistory(self, path=None, limit=10):
        if path is not None:
            st_out = self._run('status', path)
            if len(st_out) > 0 and st_out[0] == '?':
                return []

        log_args = []
        if path is not None:
            log_args.append(path)
        log_args += ['--style', self.log_style]
        log_args += ['-l', limit]
        log_out = self._run('log', *log_args)

        revisions = []
        for group in log_out.split("$$$\n"):
            if group == '':
                continue
            revisions.append(self._parseRevision(group))
        return revisions

    def getState(self, path):
        st_out = self._run('status', path)
        if len(st_out) > 0:
            if st_out[0] == '?' or st_out[0] == 'A':
                return STATE_NEW
            if st_out[0] == 'M':
                return STATE_MODIFIED
        return STATE_COMMITTED

    def getRevision(self, path, rev):
        cat_out = self._run('cat', '-r', rev, path)
        return cat_out

    def diff(self, path, rev1, rev2):
        if rev2 is None:
            diff_out = self._run('diff', '-c', rev1, '--git', path)
        else:
            diff_out = self._run('diff', '-r', rev1, '-r', rev2, '--git', path)
        return diff_out

    def commit(self, paths, op_meta):
        if 'message' not in op_meta or not op_meta['message']:
            raise ValueError("No commit message specified.")

        # Check if any of those paths needs to be added.
        st_out = self._run('status', *paths)
        add_paths = []
        for line in st_out.splitlines():
            if line[0] == '?':
                add_paths.append(line[2:])
        if len(add_paths) > 0:
            self._run('add', *paths)

        # Create a temp file with the commit message.
        f, temp = tempfile.mkstemp()
        with os.fdopen(f, 'w') as fd:
            fd.write(op_meta['message'])

        # Commit and clean up the temp file.
        try:
            commit_args = list(paths) + ['-l', temp]
            if 'author' in op_meta:
                commit_args += ['-u', op_meta['author']]
            self._run('commit', *commit_args)
        finally:
            os.remove(temp)

    def revert(self, paths=None):
        if paths is not None:
            self._run('revert', '-C', paths)
        else:
            self._run('revert', '-a', '-C')

    def _initRepo(self, path):
        self._run('init', path, norepo=True)

    def _parseRevision(self, group):
        lines = group.split("\n")

        m = re.match(r'(\d+) ([0-9a-f]+) \[([^\]]+)\] ([^ ]+)', lines[0])
        if m is None:
            raise Exception('Error parsing history from Mercurial, got: ' + lines[0])

        rev = Revision()
        rev.rev_id = int(m.group(1))
        rev.rev_name = rev.rev_id[:12]
        rev.rev_hash = m.group(2)
        rev.author = Author(m.group(3))
        rev.timestamp = float(m.group(4))

        i = 1
        rev.description = ''
        while lines[i] != '---':
            if i > 1:
                rev.description += "\n"
            rev.description += lines[i]
            i += 1

        rev.files = []
        for j in range(i + 1, len(lines)):
            if lines[j] == '':
                continue
            rev.files.append({
                'path': lines[j][2:],
                'action': self.actions[lines[j][0]]
                })

        return rev

    def _run(self, cmd, *args, **kwargs):
        exe = [self.hg]
        if 'norepo' not in kwargs or not kwargs['norepo']:
            exe += ['-R', self.root]
        exe.append(cmd)
        exe += args
        logger.debug("Running Mercurial: " + str(exe))
        return subprocess.check_output(exe)


hg_client = None
cl_lock = threading.Lock()


class MercurialCommandServerSourceControl(MercurialBaseSourceControl):
    def __init__(self, root, client=None):
        MercurialBaseSourceControl.__init__(self, root)
        self.client = client

    def _initRepo(self, root):
        exe = ['hg', 'init', root]
        logger.debug("Running Mercurial: " + str(exe))
        return subprocess.check_output(exe)

    def _doStart(self):
        if self.client is None:
            if hg_client is None:
                with cl_lock:
                    if hg_client is None:
                        self._createServer()
                self.client = hg_client
            else:
                logger.debug("Re-using existing Mercurial command server.")
                self.client = hg_client

    def _createServer(self):
        logger.debug("Spawning Mercurial command server.")
        import hglib
        global hg_client
        hg_client = hglib.open(self.root)

        def shutdown_commandserver(num, frame):
            global hg_client
            if hg_client is not None:
                with cl_lock:
                    if hg_client is not None:
                        logger.debug("Shutting down Mercurial command server.")
                        hg_client.close()
                        hg_client = None
        import atexit
        atexit.register(shutdown_commandserver, None, None)
        try:
            import signal
            signal.signal(signal.SIGTERM, shutdown_commandserver)
        except:
            # `mod_wsgi` prevents adding stuff to `SIGTERM`
            # so let's not make a big deal if this doesn't
            # go through.
            pass

    def getHistory(self, path=None, limit=10):
        if path is not None:
            with cl_lock:
                status = self.client.status(include=[path])
            if len(status) > 0 and status[0] == '?':
                return []

        needs_files = False
        if path is not None:
            with cl_lock:
                repo_revs = self.client.log(files=[path], follow=True, limit=limit)
        else:
            needs_files = True
            with cl_lock:
                repo_revs = self.client.log(follow=True, limit=limit)
        revisions = []
        for rev in repo_revs:
            r = Revision(rev.node)
            r.rev_name = rev.node[:12]
            r.author = Author(rev.author)
            r.timestamp = time.mktime(rev.date.timetuple())
            r.description = unicode(rev.desc)
            if needs_files:
                with cl_lock:
                    rev_statuses = self.client.status(change=rev.node)
                for rev_status in rev_statuses:
                    r.files.append({
                        'path': rev_status[1].decode('utf-8', 'replace'),
                        'action': self.actions[rev_status[0]]
                        })
            revisions.append(r)
        return revisions

    def getState(self, path):
        with cl_lock:
            statuses = self.client.status(include=[path])
        if len(statuses) == 0:
            return STATE_COMMITTED
        status = statuses[0]
        if status[0] == '?' or status[0] == 'A':
            return STATE_NEW
        if status[0] == 'M':
            return STATE_MODIFIED
        raise Exception("Unsupported status: %s" % status)

    def getRevision(self, path, rev):
        with cl_lock:
            return self.client.cat([path], rev=rev)

    def diff(self, path, rev1, rev2):
        with cl_lock:
            if rev2 is None:
                return self.client.diff(files=[path], change=rev1, git=True)
            return self.client.diff(files=[path], revs=[rev1, rev2], git=True)

    def commit(self, paths, op_meta):
        if 'message' not in op_meta or not op_meta['message']:
            raise ValueError("No commit message specified.")

        kwargs = {}
        if 'author' in op_meta:
            kwargs['u'] = op_meta['author']
        try:
            # We need to write our own command because somehow the `commit`
            # method in `hglib` doesn't support specifying the file(s)
            # directly -- only with `--include`. Weird.
            args = cmdbuilder('commit', *paths,
                    debug=True, m=op_meta['message'], A=True,
                    **kwargs)
            with cl_lock:
                self.client.rawcommand(args)
        except CommandError as e:
            raise SourceControlError('commit', e.out, e.args, e.out)

    def revert(self, paths=None):
        with cl_lock:
            if paths is not None:
                self.client.revert(files=paths, nobackup=True)
            else:
                self.client.revert(all=True, nobackup=True)

