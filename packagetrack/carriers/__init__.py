import os
from functools import wraps

from ..configuration import NullConfig, ConfigKeyError

__carriers = {}

class TrackingFailure(Exception):
    """Generic tracking failure, subclassed by more specific
    exceptions.
    """
    pass

class TrackingApiFailure(TrackingFailure):
    """Raised in the event of a failure with the service's API. For
    example, a SOAP fault or authentication failure. The request was
    valid but the service API returned an error.
    """
    pass

class TrackingNetworkFailure(TrackingFailure):
    """Raised for network communication failure when talking to the
    service API. For example, a network timeout or DNS resolution
    failure.
    """
    pass

class TrackingNumberFailure(TrackingFailure):
    """Raised when the request to the service API was successful, but
    the service didn't recognize the tracking number. For example the
    tracking number wasn't in the service database, even though it looks like a
    valid tracking number for the service.
    """
    pass

class UnrecognizedTrackingNumber(TrackingFailure):
    """Raised when a tracking number cannot be matched to a service.
    """
    pass

class InvalidTrackingNumber(TrackingFailure):
    """Raised when a service's track() method is called with a TN not for that
    service
    """
    pass

def register_carrier(carrier_iface, config):
    carrier = carrier_iface(config)
    __carriers[str(carrier)] = carrier
    return carrier

def identify_tracking_number(tracking_number):
    for carrier in __carriers.values():
        if carrier.identify(tracking_number):
            return carrier
    else:
        raise TrackingNumberFailure(tracking_number)

def auto_register_carriers(config):
    carrier_modules = map(lambda m: __import__(m, fromlist='*'),
        [__name__ + '.' + f.rsplit('.', 1)[0] \
            for f in os.listdir(os.path.dirname(__file__)) \
                if f.endswith('.py') and not f.startswith('_')])
    carrier_ifaces = [getattr(m, c) for m in carrier_modules \
        for c in dir(m) \
            if c.endswith('Interface') and \
                issubclass(getattr(m, c), BaseInterface) and \
                getattr(m, c) is not BaseInterface]
    for carrier_iface in carrier_ifaces:
        register_carrier(carrier_iface, config)

class BaseInterface(object):
    DEFAULT_CFG = NullConfig()

    def __init__(self, config):
        self._config = config

    def __str__(self):
        return self.LONG_NAME

    @classmethod
    def require_valid_tracking_number(cls, func):
        @wraps(func)
        def wrapper(self, tracking_number):
            if not self.identify(tracking_number):
                raise InvalidTrackingNumber(tracking_number)
            else:
                return func(self, tracking_number)
        return wrapper

    def identify(self, tracking_number):
        raise NotImplementedError()

    def track(self, tracking_number):
        raise NotImplementedError()

    def url(self, tracking_number):
        return self._url_template.format(tracking_number=tracking_number)

    def _cfg_value(self, *keys):
        try:
            value = self._config.get_value(self.CONFIG_NS, *keys)
        except ConfigKeyError as err:
            try:
                value = self.DEFAULT_CFG.get_value(self.CONFIG_NS, *keys)
            except ConfigKeyError:
                raise err
        return value
