from jinja2 import BaseLoader, ChoiceLoader

from webfluid import Fluid
from webfluid.core.freeze import Freezable

_template_path: str

class Loaders(Freezable):
    label: str
    closed_after: str
    _loaders: list[BaseLoader]
    def __init__(self, fluid: Fluid) -> None: ...
    def add(self, loader: BaseLoader) -> None: ...
    def freeze(self, value: ChoiceLoader | None = None) -> ChoiceLoader: ...
    @property
    def loader(self) -> ChoiceLoader: ...
