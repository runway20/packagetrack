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
    """Basic configuration provider interface, other providers should inherit
    from this
    """
    def get_value(self, *keys):
        raise NotImplementedError()

class NullConfig(ConfigurationProvider):
    """Simple placeholder provider, raises ConfigKeyError for all keys
    """
    def get_value(self, *keys):
        raise ConfigKeyError('NullConfig provides no values')

class DotFileConfig(ConfigurationProvider):
    """Provides compatibility with older packagetrack versions by reading
    from the .packagetrack config file. Can read from an alternative
    file as well.
    """
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

class DictConfig(ConfigurationProvider, dict):
    """Simple config provider that acts like a dict
    """
    def get_value(self, *keys):
        node = self
        for key in keys:
            try:
                node = node.get(key)
            except KeyError as err:
                raise ConfigKeyError(err)
        return node
