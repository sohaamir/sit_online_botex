import time
from functools import wraps

def safe_websocket(max_retries=3, retry_delay=1):
    def decorator(f):
        @wraps(f)
        def wrapped(player, data):
            for attempt in range(max_retries):
                try:
                    return f(player, data)
                except Exception as e:
                    if attempt == max_retries - 1:  # Only log on the last attempt
                        print(f"WebSocket error in {f.__name__} after {max_retries} attempts: {e}")
                    time.sleep(retry_delay)
            return None
        return wrapped
    return decorator