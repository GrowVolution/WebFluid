from jinja2 import BaseLoader, ChoiceLoader

from webfluid import Fluid

_template_path: str

class Loaders:
    _loaders: list[BaseLoader]
    _frozen: tuple[BaseLoader, ...] | None
    def __init__(self, fluid: Fluid) -> None: ...
    def add(self, loader: BaseLoader) -> None: ...
    def freeze(self) -> None: ...
    @property
    def loader(self) -> ChoiceLoader: ...
