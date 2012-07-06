from datetime import datetime, time
import requests

from ..configuration import DictConfig
from ..data import TrackingInfo
from ..carriers import BaseInterface
from ..xml_dict import xml_to_dict
from .errors import *

class USPSInterface(BaseInterface):
    SHORT_NAME = 'USPS'
    LONG_NAME = 'U.S. Postal Service'
    CONFIG_NS = SHORT_NAME
    DEFAULT_CFG = DictConfig({CONFIG_NS:{'server': 'production'}})

    _api_urls = {
        'secure_test': 'https://secure.shippingapis.com/ShippingAPITest.dll?' \
            'API=TrackV2&XML=',
        'test':        'http://testing.shippingapis.com/ShippingAPITest.dll?' \
            'API=TrackV2&XML=',
        'production':  'http://production.shippingapis.com/ShippingAPI.dll?' \
            'API=TrackV2&XML=',
        'secure':      'https://secure.shippingapis.com/ShippingAPI.dll?' \
            'API=TrackV2&XML=',
    }
    _service_types = {
        'EA': 'express mail',
        'EC': 'express mail international',
        'CP': 'priority mail international',
        'RA': 'registered mail',
        'RF': 'registered foreign',
#        'EJ': 'something?',
    }
    _url_template = 'http://trkcnfrm1.smi.usps.com/PTSInternetWeb/' \
        'InterLabelInquiry.do?origTrackNum={tracking_number}'
    _request_xml = '<TrackFieldRequest USERID="{userid}">' \
        '<TrackID ID="{tracking_number}"/></TrackFieldRequest>'

    def identify(self, tracking_number):
        return {
            13: lambda x: \
                x[0:2].isalpha() and x[2:9].isdigit() and x[11:13].isalpha(),
            20: lambda x: \
                x.isdigit() and x.startswith('0'),
            22: lambda x: \
                x.isdigit() and x.startswith('9') and not (x.startswith('96') or \
                    x.startswith('91')),
            30: lambda x:
                x.isdigit(),
        }.get(len(tracking_number), lambda x: False)(tracking_number)

    @BaseInterface.require_valid_tracking_number
    def track(self, tracking_number):
        resp = self._send_request(tracking_number)
        return self._parse_response(resp, tracking_number)

    def _build_request(self, tracking_number):
        return self._request_xml.format(
            userid=self._cfg_value('userid'),
            tracking_number=tracking_number)

    def _parse_response(self, raw, tracking_number):
        rsp = xml_to_dict(raw)

        # this is a system error
        if 'Error' in rsp:
            error = rsp['Error']['Description']
            raise TrackingApiFailure(error)

        # this is a result with an error, like "no such package"
        if 'Error' in rsp['TrackResponse']['TrackInfo']:
            error = rsp['TrackResponse']['TrackInfo']['Error']['Description']
            raise TrackingNumberFailure(error)

        # make sure the events list is a list
        try:
            events = rsp['TrackResponse']['TrackInfo']['TrackDetail']
        except KeyError:
            events = []
        else:
            if type(events) != list:
                events = [events]

        summary = rsp['TrackResponse']['TrackInfo']['TrackSummary']
        last_update = self._getTrackingDate(summary)
        last_location = self._getTrackingLocation(summary)

        # status is the first event's status
        status = summary['Event']

        # USPS doesn't return this, so we work it out from the tracking number
        service_code = tracking_number[0:2]
        service_description = self._service_types.get(service_code, 'USPS')

        trackinfo = TrackingInfo(
            tracking_number = tracking_number,
            delivery_date   = last_update,
            service         = service_description,
        )

        # add the last event if delivered, USPS doesn't duplicate
        # the final event in the event log, but we want it there
        if status == 'DELIVERED':
            trackinfo.create_event(
                location = last_location,
                detail = status,
                timestamp = last_update,
            )

        for e in events:
            trackinfo.create_event(
                location = self._getTrackingLocation(e),
                timestamp= self._getTrackingDate(e),
                detail   = e['Event'],
            )

        return trackinfo

    def _send_request(self, tracking_number):
        url = self._api_urls[self._cfg_value('server')] + \
            self._build_request(tracking_number)
        return requests.get(url).text

    def _getTrackingDate(self, node):
        """Returns a datetime object for the given node's
        <EventTime> and <EventDate> elements"""
        date = datetime.strptime(node['EventDate'], '%B %d, %Y').date()
        if node['EventTime']:
            time_ = datetime.strptime(node['EventTime'], '%I:%M %p').time()
        else:
            time_ = time(0,0,0)
        return datetime.combine(date, time_)


    def _getTrackingLocation(self, node):
        """Returns a location given a node that has
            EventCity, EventState, EventCountry elements"""

        return ','.join((
                node['EventCity'],
                node['EventState'],
                node['EventCountry'] or 'US'
            ))

