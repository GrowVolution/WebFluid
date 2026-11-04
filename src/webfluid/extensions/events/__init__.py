from .main import EventBus

# TODO(1.1): drop the pre-rc1 alias EventManager once 1.1 may break public names.
EventManager = EventBus

__all__ = ["EventBus"]
