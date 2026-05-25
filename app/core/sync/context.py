import threading
from contextlib import contextmanager


_state = threading.local()


def is_sync_suppressed():
    return bool(getattr(_state, 'suppressed', False))


@contextmanager
def suppress_sync_outbox():
    previous = is_sync_suppressed()
    _state.suppressed = True
    try:
        yield
    finally:
        _state.suppressed = previous
