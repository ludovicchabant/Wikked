import os.path


class EndpointInfo(object):
    def __init__(self, name):
        self.name = name
        self.query = True
        self.readonly = False
        self.builtin = False
        self.default = None
        self.root_dir = None


_resources_root_dir = os.path.join(os.path.dirname(__file__), 'resources')


SPECIAL_ENDPOINT = 'special'


def create_endpoint_infos(config):
    endpoints = {}
    sections = [s for s in config.sections() if s.startswith('endpoint:')]
    for s in sections:
        ep = EndpointInfo(s[9:])   # 9 = len('endpoint:')
        ep.query = config.getboolean(s, 'query', fallback=True)
        ep.readonly = config.getboolean(s, 'readonly', fallback=False)
        ep.default = config.get(s, 'default', fallback=None)
        if config.get(s, '__is_builtin', fallback=False):
            ep.builtin = True
            ep.root_dir = os.path.join(_resources_root_dir, ep.name)
        endpoints[ep.name] = ep
    return endpoints
