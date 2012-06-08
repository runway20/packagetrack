import suds
import packagetrack
import datetime

from ..data import TrackingInfo
from ..service import BaseInterface, TrackFailed, InvalidTrackingNumber

def get_keys(reply):
    return [k for k in dir(reply) if not k.startswith('_')]

class CanadaPostInterface(BaseInterface):
    SHORT_NAME = 'CAPost'
    LONG_NAME = 'CanadaPost'
    _config_ns = LONG_NAME
    _soap_wsdl = 'http://www.canadapost.ca/cpo/mc/assets/wsdl/developers/track.wsdl'
    _soap_endpoint = 'https://soa-gw.canadapost.ca/vis/soap/track'
    _url_template = 'http://www.canadapost.ca/cpotools/apps/track/personal/findByTrackNumber?trackingNumber={tracking_number}&LOCALE=en'
    _client = None

    def _get_client(self):
        if self._client is None:
            sec_token = suds.wsse.Security()
            sec_token.tokens.append(suds.wsse.UsernameToken(
                packagetrack.config.get(self._config_ns, 'username'),
                packagetrack.config.get(self._config_ns, 'password')))
            self._client = suds.client.Client(self._soap_wsdl,
                location=self._soap_endpoint,
                wsse=sec_token)
        return self._client

    def identify(self, tracking_number):
        """Check if a tracking number is valid for this service
        """
        return {
            15: lambda tn: tn.isdigit() and tn.startswith('9'),
            16: lambda tn: tn.isdigit(),
        }.get(len(tracking_number), lambda tn: False)(tracking_number)
    validate = identify

    def _get_keys(self, reply):
        return [k for k in dir(reply) if not k.startswith('_')]

    def _parse_response(self, summary_response, detail_response):
        if 'messages' in get_keys(summary_response):
            raise TrackFailed(summary_response['messages'])
        elif 'messages' in get_keys(detail_response):
            raise TrackFailed(detail_response['messages'])
        if 'pin-summary' in get_keys(summary_response['tracking-summary']):
            summary = summary_response['tracking-summary']['pin-summary'][0]
        else:
            summary = summary_response['tracking-summary']['dnc-summary'][0]
        details = detail_response['tracking-detail']
        delivery_date = datetime.datetime.strptime(
            details['expected-delivery-date'],
            '%Y-%m-%d')
        service = details['service-name']
        info = TrackingInfo(
            tracking_number=None,
            delivery_date=delivery_date,
            status=summary['event-type'],
            last_update=None,
            service=service
        )
        for event in details['significant-events']['occurrence'][::-1]:
            date = datetime.datetime.strptime(event['event-date'], '%Y-%m-%d').date()
            time = datetime.datetime.strptime(event['event-time'], '%H:%M:%S').time()
            info.addEvent(
                date=datetime.datetime.combine(date,time),
                detail=event['event-description'],
                location=','.join([event['event-site'], event['event-province']]))
        info.location = info.events[-1].location
        info.last_update = info.events[-1].date
        return info


    def track(self, tracking_number):
        if len(tracking_number) == 16:
            arg = dict(pin=tracking_number)
        else:
            arg = dict(dnc=tracking_number)
        client = self._get_client()
        try:
            summary = client.service.GetTrackingSummary(locale='EN', **arg)
            detail = client.service.GetTrackingDetail(locale='EN', **arg)
        except suds.WebFault as e:
            raise TrackFailed(e)
        info = self._parse_response(summary, detail)
        info.tracking_number = tracking_number
        return info

    def url(self, tracking_number):
        return self._url_template.format(tracking_number=tracking_number)
