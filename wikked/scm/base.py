
STATE_COMMITTED = 0
STATE_MODIFIED = 1
STATE_NEW = 2
STATE_NAMES = ['committed', 'modified', 'new']

ACTION_ADD = 0
ACTION_DELETE = 1
ACTION_EDIT = 2
ACTION_NAMES = ['add', 'delete', 'edit']


class SourceControl(object):
    def __init__(self):
        pass

    def initRepo(self, wiki):
        raise NotImplementedError()

    def getSpecialFilenames(self):
        raise NotImplementedError()

    def getHistory(self, path=None, limit=10):
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


class SourceControlError(Exception):
    def __init__(self, operation, message, command, output, *args):
        Exception.__init__(self, *args)
        self.operation = operation
        self.message = message
        self.command = command
        self.output = output

    def __str__(self):
        return "Error running '%s': %s\nCommand: %s\nOutput: %s" % (
                self.operation, self.message, self.command, self.output)

