from operator import attrgetter

class TrackingInfo(dict):
    """Generic tracking information object returned by a tracking request
    """

    _repr_template = '<TrackingInfo(delivery_date={i.delivery_date!r}, status={i.status!r}, last_update={i.last_update!r}, location={i.location!r})>'

    def __init__(self, tracking_number, delivery_date=None):
        self.tracking_number = tracking_number
        self.delivery_date = delivery_date
        self.events = []

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, val):
        self[name] = val

    def __repr__(self):
        # return slightly different info if it's delivered
        return self._repr_template.format(i=self)

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

    self._repr_template = '<TrackingEvent(timestamp={e.timestamp!r}, location={e.location!r}, detail={e.detail!r})>'

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
