import requests
from datetime import datetime, date, time

from ..configuration import DictConfig
from ..carriers import BaseInterface
from ..xml_dict import dict_to_xml, xml_to_dict
from ..data import TrackingInfo
from .errors import *

class UPSInterface(BaseInterface):
    SHORT_NAME = 'UPS'
    LONG_NAME = SHORT_NAME
    CONFIG_NS = SHORT_NAME
    DEFAULT_CFG = DictConfig({CONFIG_NS:{'lang': 'en-US'}})

    _api_url = 'https://wwwcie.ups.com/ups.app/xml/Track'
    _url_template = 'http://wwwapps.ups.com/WebTracking/processInputRequest?' \
        'TypeOfInquiryNumber=T&InquiryNumber1={tracking_number}'

    def identify(self, tracking_number):
        return tracking_number.startswith('1Z') and \
            tracking_number[-1].isdigit() and \
            tracking_number.isalnum() and \
            self._check_tracking_code(tracking_number[2:])

    @BaseInterface.require_valid_tracking_number
    def track(self, tracking_number):
        resp = self._send_request(tracking_number)
        return self._parse_response(resp, tracking_number)

    def _check_tracking_code(self, tracking_code):
        digits = map(lambda d: int(d) if d.isdigit() else ((ord(d) - 63) % 10),
            tracking_code[:-1].upper())
        check_digit = int(tracking_code[-1])

        total = (sum(digits[1::2]) * 2) + sum(digits[::2])
        return (10 - (total % 10)) == check_digit

    def _build_access_request(self):
        req = {
            'AccessRequest': {
                'AccessLicenseNumber': self._cfg_value('license_number'),
                'UserId': self._cfg_value('user_id'),
                'Password': self._cfg_value('password'),
            }
        }
        return dict_to_xml(req, {'xml:lang': self._cfg_value('lang')})

    def _build_track_request(self, tracking_number):
        data = {
            'TrackRequest': {
                'Request': {
                    'TransactionReference': {
                        'RequestAction': 'Track',
                    },
                    'RequestOption': '1',
                },
                'TrackingNumber': tracking_number,
            }
        }
        return dict_to_xml(data)

    def _build_request(self, tracking_number):
        return (self._build_access_request() +
                self._build_track_request(tracking_number))

    def _send_request(self, tracking_number):
        return requests.post(self._api_url, self._build_request(tracking_number)).text

    def _parse_response(self, raw, tracking_number):
        root = xml_to_dict(raw)['TrackResponse']

        response = root['Response']
        status_code = response['ResponseStatusCode']
        status_description = response['ResponseStatusDescription']
        # Check status code?

        # we need the service code, some things are treated differently
        try:
            service_code = root['Shipment']['Service']['Code']
        except KeyError:
            raise TrackingApiFailure(root)
        service_description = 'UPS %s' % root['Shipment']['Service']['Description']

        package = root['Shipment']['Package']

        # make activites a list if it's not already
        if type(package['Activity']) != list:
            package['Activity'] = [package['Activity']]

        # this is the last activity, the one we get status info from
        activity = package['Activity'][0]

        # here's the status code, inside the Activity block
        status = activity['Status']['StatusType']['Description']
        status_code = activity['Status']['StatusType']['Code']

        last_update_date = datetime.strptime(activity['Date'], "%Y%m%d").date()
        last_update_time = datetime.strptime(activity['Time'], "%H%M%S").time()
        last_update = datetime.combine(last_update_date, last_update_time)

        # 031 = BASIC service, delivered to local P.O., so we use the
        # ShipTo address to get the city, state, country
        # this may never be considered D=Delivered, best we can do
        # is just report that the local P.O. got it.
        #
        # note this also has no SDD, so we just use the last update
        if service_code == '031':
            loc = root['Shipment']['ShipTo']['Address']
        else:
            loc = activity['ActivityLocation']['Address']
        if status_code == 'M':
            last_location = 'N/A'
        else:
            last_location = []
            for key in ['City', 'StateProvinceCode', 'CountryCode']:
                try:
                    last_location.append(loc[key])
                except KeyError:
                    continue
            last_location = ','.join(last_location) if last_location else 'UNKNOWN'

        # Delivery date is the last_update if delivered, otherwise
        # the estimated delivery date
        if service_code == '031' or status_code == 'D':
            delivery_date = last_update
        elif 'RescheduledDeliveryDate' in package:
            delivery_date = datetime.strptime(
                package['RescheduledDeliveryDate'], "%Y%m%d")
        elif 'ScheduledDeliveryDate' in root['Shipment']:
            delivery_date = datetime.strptime(
                root['Shipment']['ScheduledDeliveryDate'], "%Y%m%d")
        else:
            delivery_date = None


        # Delivery detail may not always be available either
        if 'Description' in activity['ActivityLocation']:
            delivery_detail = activity['ActivityLocation']['Description']
        else:
            delivery_detail = status

        trackinfo = TrackingInfo(
            tracking_number = tracking_number,
            delivery_date   = delivery_date,
            service         = service_description,
        )

        # add a single event, UPS doesn't seem to support multiple?

        for e in package['Activity']:
            loc = e['ActivityLocation']['Address']
            location = []
            for key in ['City', 'StateProvinceCode', 'CountryCode']:
                try:
                    location.append(loc[key])
                except KeyError:
                    continue
            location = ','.join(location) if location else 'UNKNOWN'

            edate = datetime.strptime(e['Date'], "%Y%m%d").date()
            etime = datetime.strptime(e['Time'], "%H%M%S").time()
            timestamp = datetime.combine(edate, etime)
            trackinfo.create_event(
                location = location,
                detail = e['Status']['StatusType']['Description'],
                timestamp = timestamp,
            )

        return trackinfo
