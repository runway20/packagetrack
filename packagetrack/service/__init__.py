from abc import ABCMeta, abstractmethod

carriers = {}

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

def register_carrier(carrier):
    if carrier.LONG_NAME in carriers:
        raise Exception('Carrier {name} already registered'.format(
            name=carrier.LONG_NAME))
    else:
        carriers[carrier.LONG_NAME] = carrier

def identify_tracking_number(tracking_number):
    for carrier in carriers.values():
        if carrier.identify(tracking_number):
            return carrier
    else:
        raise TrackingNumberFailure(tracking_number)

class CarrierInterface(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        register_carrier(self)

    def __str__(self):
        return self.LONG_NAME

    @abstractmethod
    def identify(self, tracking_number):
        pass

    @abstractmethod
    def track(self, tracking_number):
        pass

    @abstractmethod
    def url(self, tracking_number):
        pass
