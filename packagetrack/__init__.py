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

__credits__     = ['Scott Torborg', 'Michael Stella', 'Alex Headley']
__authors__     = ', '.join(__credits__)
__license__     = 'GPL'
__maintainer__  = __credits__[2]
__status__      = 'Development'
__version__     = '0.3'

from .configuration import DotFileConfig, NullConfig
from .data import Package
from .service import auto_register_carriers

try:
    config = DotFileConfig()
except ConfigError:
    config = NullConfig()

auto_register_carriers(config)
