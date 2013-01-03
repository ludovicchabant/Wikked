import re
import os
import os.path
import logging
import tempfile
import subprocess


STATE_COMMITTED = 0
STATE_MODIFIED = 1
STATE_NEW = 2
STATE_NAMES = ['committed', 'modified', 'new']

ACTION_ADD = 0
ACTION_DELETE = 1
ACTION_EDIT = 2
ACTION_NAMES = ['add', 'delete', 'edit']


class SourceControl(object):
    def __init__(self, root, logger=None):
        self.root = root
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.scm')

    def getSpecialDirs(self):
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


class MercurialSourceControl(SourceControl):
    def __init__(self, root, logger=None):
        SourceControl.__init__(self, root, logger)
        self.hg = 'hg'
        if not os.path.isdir(os.path.join(root, '.hg')):
            self._run('init', root, norepo=True)

        ignore_path = os.path.join(root, '.hgignore')
        if not os.path.isfile(ignore_path):
            with open(ignore_path, 'w') as f:
                f.write('.cache')
            self._run('add', ignore_path)
            self._run('commit', ignore_path, '-m', 'Created .hgignore.')

        self.log_style = os.path.join(os.path.dirname(__file__), 'resources', 'hg_log.style')
        self.actions = {
                'A': ACTION_ADD,
                'R': ACTION_DELETE,
                'M': ACTION_EDIT
                }

    def getSpecialDirs(self):
        specials = [ '.hg', '.hgignore', '.hgtags' ]
        return [ os.path.join(self.root, d) for d in specials ]

    def getHistory(self, path=None):
        if path is not None:
            st_out = self._run('status', path)
            if len(st_out) > 0 and st_out[0] == '?':
                return [ Revision() ]

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
            diff_out = self._run('diff', '-c', rev1, '--git', path);
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
            commit_args = list(paths) + [ '-l', temp ]
            if 'author' in op_meta:
                commit_args += [ '-u', op_meta['author'] ]
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
            rev.files.append({ 'path': lines[j][2:], 'action': self.actions[lines[j][0]] })

        return rev

    def _run(self, cmd, *args, **kwargs):
        exe = [ self.hg ]
        if 'norepo' not in kwargs or not kwargs['norepo']:
            exe += [ '-R', self.root ]
        exe.append(cmd)
        exe += args
        self.logger.debug("Running Mercurial: " + str(exe))
        return subprocess.check_output(exe)

