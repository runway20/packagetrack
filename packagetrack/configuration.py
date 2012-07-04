import os.path
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

class ConfigError(Exception):
    """Generic configuration error exception
    """
    pass

class ConfigKeyError(KeyError):
    """Raised when a key is requested from the config but is not found
    """
    pass

class ConfigurationProvider(object):
    def get_value(self, key):
        raise NotImplementedError()

class NullConfig(ConfigurationProvider):
    def get_value(self, *keys):
        raise ConfigKeyError('NullConfig provides no values')

class DotFileConfig(ConfigurationProvider):
    _config = None

    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.expanduser('~/.packagetrack')
        if not os.path.exists(config_file):
            raise ConfigError('Config file does not exist: {file}'.format(
                file=config_file))

        self._config = ConfigParser()
        self._config.read([config_file])

    def get_value(self, *keys):
        try:
            return self._config.get(*keys)
        except (NoSectionError, NoOptionError) as err:
            raise ConfigKeyError(err)

class DictConfig(ConfigurationProvider):
    def __init__(self, config_dict):
        self._config = config_dict

    def get_value(self, *keys):
        node = self._config
        for key in keys:
            try:
                node = node.get(key)
            except KeyError as err:
                raise ConfigKeyError(err)
        return node
