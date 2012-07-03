"""A simple, generic interface to track packages.

Supported shippers:
    Federal Express, UPS, U.S. Postal Service

Basic usage:

    >>> from packagetrack import Package
    >>> package = Package('1Z9999999999999999')
    # Identify packages (UPS, FedEx, and USPS)
    >>> package.shipper
    'UPS'
    # Track packages (UPS only, requires API access)
    >>> info = package.track()
    >>> print info.status
    IN TRANSIT TO
    >>> print info.delivery_date
    2010-06-25 00:00:00
    >>> print info.last_update
    2010-06-19 00:54:00
    # Get tracking URLs (UPS, FedEx, and USPS)
    >>> print package.url()
    http://wwwapps.ups.com/WebTracking/processInputRequest?TypeOfInquiryNumber=T&InquiryNumber1=1Z9999999999999999

Configuration:

To enable package tracking, you will need to obtain an API account for
each of the services you wish to use, and then make a config file
that looks like:

    [UPS]
    license_number = XXXXXXXXXXXXXXXX
    user_id = XXXX
    password = XXXX

    [FedEx]
    key = XXXXXXXXXXXXXXXX
    password = XXXXXXXXXXXXXXXXXXXXXXXXX
    account_number = #########
    meter_number = #########

    [USPS]
    userid = XXXXXXXXXXXX
    password = XXXXXXXXXXXX


The default location for this file is ~/.packagetrack.

"""

from .configuration import DotFileConfig

__authors__     = 'Scott Torborg, Michael Stella'
__credits__     = ['Scott Torborg','Michael Stella']
__license__     = 'GPL'
__maintainer__  = 'Scott Torborg'
__status__      = 'Development'
__version__     = '0.3'

config = DotFileConfig()

class Package(object):
    """A package to be tracked."""

    _carrier = None

    def __init__(self, tracking_number):
        self.tracking_number = tracking_number

    @property
    def shipper(self):
        if self._carrier is None:
            self._carrier = service.identify_tracking_number(
                self.tracking_number)
        return self._carrier

    def track(self):
        """Tracks the package, returning a TrackingInfo object"""

        return self.shipper.track(self.tracking_number)

    @property
    def url(self):
        """Returns a URL that can be used to go to the shipper's
        tracking website, to track this package."""

        return self.shipper.url(self.tracking_number)
