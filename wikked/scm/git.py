import os
import os.path
import logging
import subprocess
from .base import (
        SourceControl,
        STATE_NEW, STATE_MODIFIED, STATE_COMMITTED)

try:
    import pygit2
    SUPPORTS_GIT = True
except ImportError:
    SUPPORTS_GIT = False


logger = logging.getLogger(__name__)


class GitBaseSourceControl(SourceControl):
    def __init__(self, root):
        SourceControl.__init__(self)
        self.root = root

    def start(self, wiki):
        # Make a Git repo if there's none.
        if not os.path.isdir(os.path.join(self.root, '.git')):
            logger.info("Creating Git repository at: " + self.root)
            self._initRepo(self.root)

        # Create a `.gitignore` file there's none.
        ignore_path = os.path.join(self.root, '.gitignore')
        if not os.path.isfile(ignore_path):
            logger.info("Creating `.gitignore` file.")
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
        logger.debug("Running Git: " + str(exe))
        return subprocess.check_output(exe)


class GitLibSourceControl(GitBaseSourceControl):
    def __init__(self, root):
        if not SUPPORTS_GIT:
            raise Exception("Can't support Git because pygit2 is not available.")
        GitBaseSourceControl.__init__(self, root)

    def initRepo(self, wiki):
        GitBaseSourceControl.initRepo(self, wiki)
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

