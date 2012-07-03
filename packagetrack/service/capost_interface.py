import suds
import datetime

from packagetrack import config
from ..data import TrackingInfo
from ..service import CarrierInterface, TrackingFailure

class CanadaPostInterface(CarrierInterface):
    SHORT_NAME = 'CAPost'
    LONG_NAME = 'CanadaPost'
    _config_ns = LONG_NAME
    _soap_wsdl = 'http://www.canadapost.ca/cpo/mc/assets/wsdl/developers/track.wsdl'
    _soap_endpoint = 'https://soa-gw.canadapost.ca/vis/soap/track'
    _url_template = 'http://www.canadapost.ca/cpotools/apps/track/'
        'personal/findByTrackNumber?trackingNumber={tracking_number}&LOCALE=en'
    _client = None

    def __init__(self):
        super(self, CanadaPostInterface).__init__()
        self._username = config.get_value(self._config_ns, 'username')
        self._password = config.get_value(self._config_ns, 'password')

    def identify(self, tracking_number):
        """Check if a tracking number is valid for this service
        """
        return {
            11: lambda tn: tn[:2].isalpha() and tn.endswith('CA'),
            13: lambda tn: tn[:2].isalpha() and tn.endswith('CA'),
            16: lambda tn: tn.isdigit(),
        }.get(len(tracking_number), lambda tn: False)(tracking_number)

    def track(self, tracking_number):
        client = self._get_client()
        try:
            summary = client.service.GetTrackingSummary(
                locale='EN', pin=tracking_number)
            detail = client.service.GetTrackingDetail(
                locale='EN', pin=tracking_number)
        except suds.WebFault as e:
            raise TrackFailed(e)
        info = self._parse_response(summary, detail)
        info.tracking_number = tracking_number
        return info

    def url(self, tracking_number):
        return self._url_template.format(tracking_number=tracking_number)

    def _get_client(self):
        if self._client is None:
            sec_token = suds.wsse.Security()
            sec_token.tokens.append(suds.wsse.UsernameToken(
                self._username, self._password))
            self._client = suds.client.Client(self._soap_wsdl,
                location=self._soap_endpoint,
                wsse=sec_token)
        return self._client

    def _get_keys(self, reply):
        return [k for k in dir(reply) if not k.startswith('_')]

    def _parse_response(self, summary_response, detail_response):
        if 'messages' in self.get_keys(summary_response):
            raise TrackFailed(summary_response['messages'])
        elif 'messages' in self.get_keys(detail_response):
            raise TrackFailed(detail_response['messages'])
        summary = summary_response['tracking-summary']['pin-summary'][0]
        details = detail_response['tracking-detail']
        delivery_date = datetime.datetime.strptime(
            details['expected-delivery-date'],
            '%Y-%m-%d')
        service = details['service-name']
        info = TrackingInfo(
            tracking_number=None,
            delivery_date=delivery_date,
            status=summary['event-type'],
            service=service
        )
        for event in details['significant-events']['occurrence'][::-1]:
            date = datetime.datetime.strptime(event['event-date'], '%Y-%m-%d').date()
            time = datetime.datetime.strptime(event['event-time'], '%H:%M:%S').time()
            info.create_event(
                timestamp=datetime.datetime.combine(date,time),
                detail=event['event-description'],
                location=','.join([event['event-site'], event['event-province']]))
        return info


