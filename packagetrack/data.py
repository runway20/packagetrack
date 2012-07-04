from operator import attrgetter

from .carriers import identify_tracking_number

class Package(object):
    """A package to be tracked."""

    _carrier = None

    def __init__(self, tracking_number, carrier=None):
        self.tracking_number = tracking_number
        if carrier is not None:
            self._carrier = carrier

    @property
    def carrier(self):
        if self._carrier is None:
            self._carrier = identify_tracking_number(
                self.tracking_number)
        return self._carrier

    def track(self):
        """Tracks the package, returning a TrackingInfo object"""

        return self.carrier.track(self.tracking_number)

    @property
    def url(self):
        """Returns a URL that can be used to go to the carrier's
        tracking website, to track this package."""

        return self.carrier.url(self.tracking_number)

class TrackingInfo(dict):
    """Generic tracking information object returned by a tracking request
    """

    _repr_template = '<TrackingInfo(delivery_date={i.delivery_date!r}, status={i.status!r}, last_update={i.last_update!r}, location={i.location!r})>'

    def __init__(self, tracking_number, delivery_date=None, **kwargs):
        self.tracking_number = tracking_number
        self.delivery_date = delivery_date
        self.events = []
        self.update(kwargs)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, val):
        self[name] = val

    def __repr__(self):
        # return slightly different info if it's delivered
        return self._repr_template.format(i=self)

    @property
    def location(self):
        return self.events[-1].location

    @property
    def last_update(self):
        return self.events[-1].timestamp

    @property
    def status(self):
        return self.events[-1].detail

    def create_event(self, timestamp, location, detail, **kwargs):
        event = TrackingEvent(timestamp, location, detail)
        event.update(kwargs)
        return self.add_event(event)

    def add_event(self, event):
        self.events = self.sort_events(self.events + [event])
        return event

    def sort_events(self, events=None):
        if events is None:
            events = self.events
        return sorted(events, key=attrgetter('timestamp'))

class TrackingEvent(dict):
    """An individual tracking event, i.e. a status change
    """
    _repr_template = '<TrackingEvent(timestamp={e.timestamp!r}, location={e.location!r}, detail={e.detail!r})>'


    def __init__(self, timestamp, location, detail, **kwargs):
        self.timestamp = timestamp
        self.location = location
        self.detail = detail
        self.update(kwargs)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, val):
        self[name] = val

    def __repr__(self):
        return self._repr_template.format(e=self)
