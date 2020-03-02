"""Class to represent an event on the Dynet network."""
import json


class DynetEvent:
    """Class to represent an event on the Dynet network."""

    def __init__(self, event_type=None, message=None, data=None):
        """Initialize the event."""
        self.event_type = event_type.upper() if event_type else None
        self.msg = message
        self.data = data

    def __repr__(self):
        """Print the event."""
        return json.dumps(self.__dict__)
