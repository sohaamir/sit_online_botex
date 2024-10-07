import time
from functools import wraps
from asgiref.sync import async_to_sync

def safe_websocket(max_retries=3, retry_delay=1):
    def decorator(f):
        @wraps(f)
        def wrapped(player, data):
            for attempt in range(max_retries):
                try:
                    return f(player, data)
                except Exception as e:
                    print(f"WebSocket error in {f.__name__} (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        try:
                            async_to_sync(player.group.session.get_consumer().close)()
                        except Exception as close_error:
                            print(f"Error closing WebSocket: {close_error}")
            return None
        return wrapped
    return decorator