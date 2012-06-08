from ..service import BaseInterface, TrackFailed, InvalidTrackingNumber

class CanadaPostInterface(BaseInterface):
    _url_template = 'http://www.canadapost.ca/cpotools/apps/track/personal/findByTrackNumber?trackingNumber={tracking_number}&LOCALE=en'

    def identify(self, tn):
        """Check if a tracking number is valid for this service
        """

        return len(tn) == 16 and tn.isdigit()
    validate = identify

    def track(self, tracking_number):
        pass

    def url(self, tracking_number):
        return self._url_template.format(tracking_number=tracking_number)
