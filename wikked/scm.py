import re
import os
import os.path
import time
import logging
import tempfile
import subprocess

try:
    import pygit2
    SUPPORTS_GIT = True
except ImportError:
    SUPPORTS_GIT = False


STATE_COMMITTED = 0
STATE_MODIFIED = 1
STATE_NEW = 2
STATE_NAMES = ['committed', 'modified', 'new']

ACTION_ADD = 0
ACTION_DELETE = 1
ACTION_EDIT = 2
ACTION_NAMES = ['add', 'delete', 'edit']


class SourceControl(object):
    def __init__(self, logger=None):
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.scm')

    def initRepo(self):
        raise NotImplementedError()

    def getSpecialFilenames(self):
        raise NotImplementedError()

    def getHistory(self, path=None):
        raise NotImplementedError()

    def getState(self, path):
        raise NotImplementedError()

    def getRevision(self, path, rev):
        raise NotImplementedError()

    def diff(self, path, rev1, rev2):
        raise NotImplementedError()

    def commit(self, paths, op_meta):
        raise NotImplementedError()

    def revert(self, paths=None):
        raise NotImplementedError()


class Revision(object):
    def __init__(self, rev_id=-1):
        self.rev_id = rev_id
        self.rev_name = rev_id
        self.author = None
        self.timestamp = 0
        self.description = None
        self.files = []

    @property
    def is_local(self):
        return self.rev_id == -1

    @property
    def is_committed(self):
        return self.rev_id != -1


class MercurialBaseSourceControl(SourceControl):
    def __init__(self, root, logger=None):
        SourceControl.__init__(self, logger)
        self.root = root
        self.actions = {
                'A': ACTION_ADD,
                'R': ACTION_DELETE,
                'M': ACTION_EDIT
                }

    def initRepo(self):
        # Make a Mercurial repo if there's none.
        if not os.path.isdir(os.path.join(self.root, '.hg')):
            self.logger.info("Creating Mercurial repository at: " + self.root)
            self._run('init', self.root, norepo=True)

        # Create a `.hgignore` file is there's none.
        ignore_path = os.path.join(self.root, '.hgignore')
        if not os.path.isfile(ignore_path):
            self.logger.info("Creating `.hgignore` file.")
            with open(ignore_path, 'w') as f:
                f.write('.wiki')
            self._run('add', ignore_path)
            self._run('commit', ignore_path, '-m', 'Created .hgignore.')

    def getSpecialFilenames(self):
        specials = ['.hg', '.hgignore', '.hgtags']
        return [os.path.join(self.root, d) for d in specials]

    def _run(self, cmd, *args, **kwargs):
        exe = [self.hg]
        if 'norepo' not in kwargs or not kwargs['norepo']:
            exe += ['-R', self.root]
        exe.append(cmd)
        exe += args
        self.logger.debug("Running Mercurial: " + str(exe))
        return subprocess.check_output(exe)


class MercurialSourceControl(MercurialBaseSourceControl):
    def __init__(self, root, logger=None):
        MercurialBaseSourceControl.__init__(self, root, logger)

        self.hg = 'hg'
        self.log_style = os.path.join(os.path.dirname(__file__), 'resources', 'hg_log.style')

    def getHistory(self, path=None):
        if path is not None:
            st_out = self._run('status', path)
            if len(st_out) > 0 and st_out[0] == '?':
                return []

        log_args = []
        if path is not None:
            log_args.append(path)
        log_args += ['--style', self.log_style]
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

    def _parseRevision(self, group):
        lines = group.split("\n")

        m = re.match(r'(\d+) ([0-9a-f]+) \[([^\]]+)\] ([^ ]+)', lines[0])
        if m is None:
            raise Exception('Error parsing history from Mercurial, got: ' + lines[0])

        rev = Revision()
        rev.rev_id = int(m.group(1))
        rev.rev_name = rev.rev_id[:12]
        rev.rev_hash = m.group(2)
        rev.author = m.group(3)
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


class MercurialCommandServerSourceControl(MercurialBaseSourceControl):
    def __init__(self, root, logger=None):
        MercurialBaseSourceControl.__init__(self, root, logger)

        import hglib
        self.client = hglib.open(self.root)

    def getHistory(self, path=None):
        if path is not None:
            rel_path = os.path.relpath(path, self.root)
            status = self.client.status(include=[rel_path])
            if len(status) > 0 and status[0] == '?':
                return []

        needs_files = False
        if path is not None:
            repo_revs = self.client.log(files=[path], follow=True)
        else:
            needs_files = True
            repo_revs = self.client.log(follow=True)
        revisions = []
        for rev in repo_revs:
            r = Revision(rev.node)
            r.rev_name = rev.node[:12]
            r.author = unicode(rev.author)
            r.timestamp = time.mktime(rev.date.timetuple())
            r.description = unicode(rev.desc)
            if needs_files:
                rev_statuses = self.client.status(change=rev.node)
                for rev_status in rev_statuses:
                    r.files.append({
                        'path': rev_status[1].decode('utf-8', 'replace'),
                        'action': self.actions[rev_status[0]]
                        })
            revisions.append(r)
        return revisions

    def getState(self, path):
        rel_path = os.path.relpath(path, self.root)
        statuses = self.client.status(include=[rel_path])
        if len(statuses) == 0:
            return STATE_COMMITTED
        status = statuses[0]
        if status[0] == '?' or status[0] == 'A':
            return STATE_NEW
        if status[0] == 'M':
            return STATE_MODIFIED
        raise Exception("Unsupported status: %s" % status)
            
    def getRevision(self, path, rev):
        rel_path = os.path.relpath(path, self.root)
        return self.client.cat([rel_path], rev=rev)

    def diff(self, path, rev1, rev2):
        rel_path = os.path.relpath(path, self.root)
        if rev2 is None:
            return self.client.diff(files=[rel_path], change=rev1, git=True)
        return self.client.diff(files=[rel_path], revs=[rev1, rev2], git=True)

    def commit(self, paths, op_meta):
        if 'message' not in op_meta or not op_meta['message']:
            raise ValueError("No commit message specified.")

        # Get repo-relative paths.
        rel_paths = [os.path.relpath(p, self.root) for p in paths]

        # Check if any of those paths needs to be added.
        status = self.client.status(unknown=True)
        add_paths = []
        for s in status:
            if s[1] in rel_paths:
                add_paths.append(s[1])
        if len(add_paths) > 0:
            self.client.add(files=add_paths)

        # Commit!
        if 'author' in op_meta:
            self.client.commit(include=rel_paths, message=op_meta['message'], user=op_meta['author'])
        else:
            self.client.commit(include=rel_paths, message=op_meta['message'])

    def revert(self, paths=None):
        if paths is not None:
            rel_paths = [os.path.relpath(p, self.root) for p in paths]
            self.client.revert(files=rel_paths, nobackup=True)
        else:
            self.client.revert(all=True, nobackup=True)


class GitBaseSourceControl(SourceControl):
    def __init__(self, root, logger=None):
        SourceControl.__init__(self, logger)
        self.root = root

    def initRepo(self):
        # Make a Git repo if there's none.
        if not os.path.isdir(os.path.join(self.root, '.git')):
            self.logger.info("Creating Git repository at: " + self.root)
            self._initRepo(self.root)

        # Create a `.gitignore` file there's none.
        ignore_path = os.path.join(self.root, '.gitignore')
        if not os.path.isfile(ignore_path):
            self.logger.info("Creating `.gitignore` file.")
            with open(ignore_path, 'w') as f:
                f.write('.wiki')
            self._add(ignore_path)
            self._commit('Created .gitignore.', [ignore_path])

    def getSpecialFilenames(self):
        specials = ['.git', '.gitignore']
        return [os.path.join(self.root, d) for d in specials]

    def getState(self, path):
        return self._status(path)

    def _run(self, cmd, *args, **kwargs):
        exe = [self.git]
        if 'norepo' not in kwargs or not kwargs['norepo']:
            exe.append('--git-dir="%s"' % self.root)
        exe.append(cmd)
        exe += args
        self.logger.debug("Running Git: " + str(exe))
        return subprocess.check_output(exe)


class GitLibSourceControl(GitBaseSourceControl):
    def __init__(self, root, logger=None):
        if not SUPPORTS_GIT:
            raise Exception("Can't support Git because pygit2 is not available.")
        GitBaseSourceControl.__init__(self, root, logger)

    def initRepo(self):
        GitBaseSourceControl.initRepo(self)
        self.repo = pygit2.Repository(self.root)

    def _initRepo(self, path):
        pygit2.init_repository(path, False)

    def _add(self, paths):
        pass

    def _commit(self, message, paths):
        pass

    def _status(self, path):
        flags = self.repo.status_file(self._getRepoPath(path))
        if flags == pygit2.GIT_STATUS_CURRENT:
            return STATE_COMMITTED
        if (flags & pygit2.GIT_STATUS_WT_MODIFIED or
                flags & pygit2.GIT_STATUS_INDEX_MODIFIED):
            return STATE_MODIFIED
        if (flags & pygit2.GIT_STATUS_WT_NEW or
                flags & pygit2.GIT_STATUS_INDEX_NEW):
            return STATE_NEW
        raise Exception("Unsupported status flag combination: %s" % flags)

    def _getRepoPath(self, path):
        return os.path.relpath(path, self.root).replace('\\', '/')

