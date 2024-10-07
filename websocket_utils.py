import asyncio
from functools import wraps
from asgiref.sync import async_to_sync

def safe_websocket(max_retries=3, retry_delay=1):
    def decorator(f):
        @wraps(f)
        def wrapped(player, data):
            print(f"Entering safe_websocket wrapper for {f.__name__}")
            for attempt in range(max_retries):
                try:
                    result = f(player, data)
                    print(f"Exiting safe_websocket wrapper for {f.__name__}")
                    return result
                except Exception as e:
                    print(f"WebSocket error in {f.__name__} (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"Max retries reached. Closing WebSocket.")
                        try:
                            async_to_sync(player.group.session.get_consumer().close)()
                            print(f"WebSocket closed for {f.__name__}")
                        except Exception as close_error:
                            print(f"Error closing WebSocket in {f.__name__}: {close_error}")
            return None
        return wrapped
    return decorator