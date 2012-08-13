import sys
from .configuration import ConfigError, DotFileConfig, NullConfig
from .data import Package
from .carriers import auto_register_carriers

try:
    config = DotFileConfig()
except ConfigError:
    config = NullConfig()

auto_register_carriers(config)

for tn in sys.argv[1:]:
    try:
        pkg = Package(tn)
        print pkg
        info = pkg.track()
        print info
        print info.events
    except Exception as err:
        print 'ERROR: %s' % err
