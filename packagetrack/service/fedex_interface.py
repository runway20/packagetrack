from datetime import datetime, date, time

from fedex.config import FedexConfig
from fedex.base_service import FedexError
from fedex.services.track_service import FedexTrackRequest, FedexInvalidTrackingNumber

import packagetrack
from ..data import TrackingInfo
from ..service import CarrierInterface, TrackingApiFailure, UnrecognizedTrackingNumber, InvalidTrackingNumber

class FedexInterface(CarrierInterface):
    SHORT_NAME = 'FedEx'
    LONG_NAME = SHORT_NAME

    _config_ns = SHORT_NAME
    _url_template = 'http://www.fedex.com/Tracking?tracknumbers={tn}'

    def __init__(self):
        super(self, CanadaPostInterface).__init__()
        self._username = config.get_value(self._config_ns, 'username')

    def track(self, tracking_number):
        if not self.validate(tracking_number):
            raise InvalidTrackingNumber()

        track = FedexTrackRequest(self._get_cfg())

        track.TrackPackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
        track.TrackPackageIdentifier.Value = tracking_number
        track.IncludeDetailedScans = True

        # Fires off the request, sets the 'response' attribute on the object.
        try:
            track.send_request()
        except FedexInvalidTrackingNumber as err:
            raise UnrecognizedTrackingNumber(err)
        except FedexError as err:
            raise TrackingApiFailure(err)

        # TODO: I haven't actually seen an unsuccessful query yet
        if track.response.HighestSeverity != "SUCCESS":
            raise TrackingApiFailure("%d: %s" % (
                    track.response.Notifications[0].Code,
                    track.response.Notifications[0].LocalizedMessage
                    ))

        return self._parse_response(track.response.TrackDetails[0], tracking_number)

    def identify(self, tracking_number):
        """Validate the tracking number"""

        return {
            12: self._validate_express,
            15: self._validate_ground96,
            20: lambda x: x.startswith('96') and self._validate_ground96(x),
            22: lambda x: x.startswith('91') or (x.startswith('00') and \
                self._validate_ssc18(x)),
        }.get(len(tracking_number), lambda x: False)(tracking_number)

    def url(self, tracking_number):
        return self._url_template.format(tn=tracking_number)

    def _parse_response(self, rsp, tracking_number):
        """Parse the track response and return a TrackingInfo object"""

        # test status code, return actual delivery time if package
        # was delivered, otherwise estimated target time
        if rsp.StatusCode == 'DL':
            delivery_date = rsp.ActualDeliveryTimestamp

            # this may not be present
            try:
                delivery_detail = rsp.Events[0].StatusExceptionDescription
            except AttributeError:
                delivery_detail = None

            last_update = delivery_date
            try:
                location = ','.join((
                                    rsp.ActualDeliveryAddress.City,
                                    rsp.ActualDeliveryAddress.StateOrProvinceCode,
                                    rsp.ActualDeliveryAddress.CountryCode,
                                ))
            except AttributeError:
                location = 'N/A'

        else:
            delivery_detail = None
            try:
                delivery_date = rsp.EstimatedDeliveryTimestamp
            except AttributeError:
                delivery_date = None
            last_update = rsp.Events[0].Timestamp
            location = self._getTrackingLocation(rsp.Events[0])


        # a new tracking info object
        trackinfo = TrackingInfo(
            tracking_number = tracking_number,
            delivery_date   = delivery_date,
            delivery_detail = delivery_detail,
            service         = rsp.ServiceType,
        )

        # now add the events
        for e in rsp.Events:
            trackinfo.create_event(
                location = self._getTrackingLocation(e),
                timestamp= e.Timestamp,
                detail   = e.EventDescription,
            )

        return trackinfo


    def _getTrackingLocation(self, e):
        """Returns a nicely formatted location for a given event"""
        try:
            return ','.join((
                            e.Address.City,
                            e.Address.StateOrProvinceCode,
                            e.Address.CountryCode,
                        ))
        except:
            return None


    def _get_cfg(self):
        """Makes and returns a FedexConfig object from the packagetrack
           configuration.  Caches it, so it doesn't create each time."""

        config = packagetrack.config

        # got one cached, so just return it
        if self.cfg:
            return self.cfg

        self.cfg = FedexConfig(
            key                 = config.get('FedEx', 'key'),
            password            = config.get('FedEx', 'password'),
            account_number      = config.get('FedEx', 'account_number'),
            meter_number        = config.get('FedEx', 'meter_number'),
            use_test_server     = False,
            express_region_code = 'US',
        )

        # these are optional, and afaik, not really used for tracking
        # at all, but you can still set them, so....
        if config.has_option('FedEx', 'express_region_code'):
            self.cfg.express_region_code = config.get('FedEx',
                                            'express_region_code')

        if config.has_option('FedEx', 'integrator_id'):
            self.cfg.integrator_id = config.get('FedEx',
                                            'integrator_id')

        if config.has_option('FedEx', 'use_test_server'):
            self.cfg.use_test_server = config.getboolean('FedEx',
                                            'use_test_server')

        return self.cfg

    def _validate_ground96(self, tracking_number):
        """Validates ground code 128 ("96") bar codes

            15-digit form:

                    019343586678996
        shipper ID: -------
        package ID:        -------
        checksum:                 -

                22-digit form:
                    9611020019343586678996
        UCC/EAN id: --
        SCNC:         --
        class of svc:   --
        shipper ID:        -------
        package ID:               -------
        checksum:                        -

        """

        rev = tracking_number[::-1]

        eventotal = 0
        oddtotal = 0
        for i in range(1,15):
            if i % 2:
                eventotal += int(rev[i])
            else:
                oddtotal += int(rev[i])

        check = 10 - ((eventotal * 3 + oddtotal) % 10)

        # compare with the checksum digit, which is the last digit
        return check == int(tracking_number[-1:])

    def _validate_ssc18(self, tracking_number):
        """Validates SSC18 tracking numbers"""

        rev = tracking_number[::-1]

        eventotal = 0
        oddtotal = 0
        for i in range(1,19):
            if i % 2:
                eventotal += int(rev[i])
            else:
                oddtotal += int(rev[i])

        check = 10 - ((eventotal * 3 + oddtotal) % 10)

        # compare with the checksum digit, which is the last digit
        return check == int(tracking_number[-1:])


    def _validate_express(self, tracking_number):
        """Validates Express tracking numbers"""

        basenum = tracking_number[0:10]

        sums = []
        mult = 1
        total = 0
        for digit in basenum[::-1]:
            sums.append(int(digit) * mult)
            total = total + (int(digit) * mult)

            if mult == 1: mult = 3
            if mult == 3: mult = 7
            if mult == 7: mult = 1

        check = total % 11
        if check == 10:
            check = 0

        # compare with the checksum digit, which is the last digit
        return check == int(tracking_number[-1:])

