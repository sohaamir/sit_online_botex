from functools import wraps
from asgiref.sync import async_to_sync

def safe_websocket(f):
    @wraps(f)
    def wrapped(player, data):
        try:
            return f(player, data)
        except Exception as e:
            print(f"WebSocket error: {e}")
            # Attempt to close the websocket gracefully
            try:
                async_to_sync(player.group.session.get_consumer().close)()
            except Exception as close_error:
                print(f"Error closing WebSocket: {close_error}")
        return None
    return wrapped