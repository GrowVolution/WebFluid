from typing import Any

config_map: dict[int, list[type]]

class ConfigMeta(type): ...

class Config(dict[str, Any]):
    def from_object(self, obj: object | str) -> None: ...
