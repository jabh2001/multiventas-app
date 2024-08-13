from flask import Response, request
from werkzeug.datastructures import ResponseCacheControl
from collections import deque
from queue import Queue

def encode_sse(data, event=None) -> str:
    line=f"data: {data}\n\n"
    if event:
        line = f"event: {event}\n{line}"
    return line
    
class Channel(object):
    def __init__(self, history_size=32):
        self.subscriptions = dict()
        
    def close_connection_message(self):
        return encode_sse("Your connection was close", "close-connection")

    def blank_event(self):
        return encode_sse(" ", "blank")

    def notify(self, message, event = None, user_id=None):
        sse = encode_sse(message, event)
        user_id = str(user_id)
        if user_id and user_id in self.subscriptions:
            q = self.subscriptions[user_id]
            q.put(sse)
        elif not user_id:
            for sub in [s for s in self.subscriptions.values()]:
                sub.put(sse)

    def attach(self, user_id):
        """Attach a new subscriber to the channel."""
        q = Queue()
        self.subscriptions.setdefault(str(user_id), q)
        q.put(encode_sse("Welcome message", "welcome"))
        return q
    
    def detach(self, user_id):
        try:
            del self.subscriptions[user_id]
        except KeyError:
            pass # Ignore unregistered users.

channel = Channel()