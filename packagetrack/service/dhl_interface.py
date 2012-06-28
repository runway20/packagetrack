import datetime
import packagetrack

from ..data import TrackingInfo
from ..service import BaseInterface, TrackFailed, InvalidTrackingNumber

class DHLInterface(BaseInterface):
    SHORT_NAME = 'DHL'
    LONG_NAME = 'DHL'

    _config_ns = LONG_NAME
    _url_template = ''

    def identify(self, tracking_number):
        return len(tracking_number) == 10 and tracking_number.isdigit()

    def track(self, tracking_number):
        pass

    def url(self, tracking_number):
        return self._url_template.format(tn=tracking_number)
