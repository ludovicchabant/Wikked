import re
import os
import os.path
import logging
import tempfile
import subprocess


STATE_COMMITTED = 0
STATE_MODIFIED = 1
STATE_NEW = 2

class SourceControl(object):
    def __init__(self, root, logger=None):
        self.root = root
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.scm')

    def getSpecialDirs(self):
        raise NotImplementedError()

    def getHistory(self, path):
        raise NotImplementedError()

    def getState(self, path):
        raise NotImplementedError()

    def commit(self, paths, op_meta):
        raise NotImplementedError()

    def revert(self, paths=None):
        raise NotImplementedError()


class PageRevision(object):
    def __init__(self, rev_id=-1):
        self.rev_id = rev_id
        self.author = None
        self.timestamp = 0
        self.description = None

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

    def getSpecialDirs(self):
        return [ os.path.join(self.root, '.hg') ]

    def getHistory(self, path):
        st_out = self._run('status', path)
        if len(st_out) > 0 and st_out[0] == '?':
            return [ PageRevision() ]

        revisions = []
        log_out = self._run('log', path, '--template', '{rev} {node} [{author}] {date|localdate} {desc}\n')
        for line in log_out.splitlines():
            m = re.match(r'(\d+) ([0-9a-f]+) \[([^\]]+)\] ([^ ]+) (.*)', line)
            if m is None:
                raise Exception('Error parsing history from Mercurial, got: ' + line)
            rev = PageRevision()
            rev.rev_id = int(m.group(1))
            rev.rev_hash = m.group(2)
            rev.author = m.group(3)
            rev.timestamp = float(m.group(4))
            rev.description = m.group(5)
            revisions.append(rev)
        return revisions

    def getState(self, path):
        st_out = self._run('status', path)
        if len(st_out) > 0:
            if st_out[0] == '?' or st_out[0] == 'A':
                return STATE_NEW
            if st_out[0] == 'M':
                return STATE_MODIFIED
        return STATE_COMMITTED

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
            self.logger.debug("Saving message: " + op_meta['message'])
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

    def _run(self, cmd, *args, **kwargs):
        exe = [ self.hg ]
        if 'norepo' not in kwargs or not kwargs['norepo']:
            exe += [ '-R', self.root ]
        exe.append(cmd)
        exe += args
        self.logger.debug("Running Mercurial: " + str(exe))
        return subprocess.check_output(exe)

