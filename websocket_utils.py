# Prevent the WebSocket from crashing the server when an error occurs
# In response to OSError: [Errno 107] Transport endpoint is not connected

from functools import wraps
from asgiref.sync import async_to_sync

def safe_websocket(f):
    @wraps(f)
    def wrapped(player, data):
        print(f"Entering safe_websocket wrapper for {f.__name__}")
        try:
            result = f(player, data)
            print(f"Exiting safe_websocket wrapper for {f.__name__}")
            return result
        except Exception as e:
            print(f"WebSocket error in {f.__name__}: {e}")
            try:
                async_to_sync(player.group.session.get_consumer().close)()
                print(f"WebSocket closed for {f.__name__}")
            except Exception as close_error:
                print(f"Error closing WebSocket in {f.__name__}: {close_error}")
        return None
    return wrapped