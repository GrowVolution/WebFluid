from importlib import import_module

config_map = {}
class ConfigMeta(type): pass


class Config(dict):
    def from_object(self, obj):
        if isinstance(obj, str):
            obj = import_module(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)
