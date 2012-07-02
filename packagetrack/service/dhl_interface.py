import datetime
import pytz
import urllib
import hashlib
import packagetrack

from ..data import TrackingInfo
from ..xml_dict import xml_to_dict
from ..service import BaseInterface, TrackFailed, InvalidTrackingNumber

class DHLInterface(BaseInterface):
    SHORT_NAME = 'DHL'
    LONG_NAME = 'DHL'

    _config_ns = LONG_NAME
    _url_template = 'http://www.dhl.com/content/g0/en/express/tracking.shtml?brand=DHL&AWB={tn}'

    _site_id = 'DServiceVal'
    _password = 'testServVal'
    _language_code = 'en'
    _tz = pytz.timezone('America/Detroit')
    _request_url = 'https://xmlpitest-ea.dhl.com/XMLShippingServlet'
    _request_template = '''<?xml version="1.0" encoding="UTF-8"?>
<req:KnownTrackingRequest xmlns:req="http://www.dhl.com"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://www.dhl.com
                        TrackingRequestKnown.xsd">
    <Request>
        <ServiceHeader>
            <MessageTime>{message_time}</MessageTime>
            <MessageReference>{message_reference}</MessageReference>
            <SiteID>{site_id}</SiteID>
            <Password>{password}</Password>
        </ServiceHeader>
    </Request>
    <LanguageCode>{language_code}</LanguageCode>
    <AWBNumber>{awb_number}</AWBNumber>
    <LevelOfDetails>ALL_CHECK_POINTS</LevelOfDetails>
    <PiecesEnabled>S</PiecesEnabled>
</req:KnownTrackingRequest>'''

    def identify(self, tracking_number):
        return {
            10: lambda tn: tn.isdigit(),
            11: lambda tn: tn.isdigit(),
        }.get(len(tracking_number), lambda tn: False)(tracking_number)

    def track(self, tracking_number):
        req = self._format_request(tracking_number)
        print req
        api_tx = urllib.urlopen(self._request_url, req)
        resp = api_tx.read().strip()
        api_tx.close()
        return self._parse_response(resp)

    def url(self, tracking_number):
        return self._url_template.format(tn=tracking_number)

    def _parse_response(self, raw_api_response):
        resp = xml_to_dict(raw_api_response)['req:TrackingResponse']
        tracking_number = resp['AWBInfo']['AWBNumber']


        # tracking_info = TrackingInfo(
        #     tracking_number=awb_number,
        #     last_update,
        #     delivery_date,
        #     status,
        #     location,
        #     delivery_detail,
        #     service
        # )

        # return tracking_info

    def _format_request(self, awb_number, language_code='en'):
        message_time = datetime.datetime.now(self._tz).replace(microsecond=0).isoformat()
        message_reference = self._generate_message_reference(awb_number, message_time)
        return self._request_template.format(
            message_time=message_time,
            message_reference=message_reference,
            site_id=self._site_id,
            password=self._password,
            language_code=self._language_code,
            awb_number=awb_number)

    def _generate_message_reference(self, awb_number, message_time):
        return hashlib.md5('|'.join(
            [awb_number, message_time, self._site_id, self._password])).hexdigest()
