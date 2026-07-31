from markupsafe import Markup

from webfluid.core.freeze import Freezable

class Sources(Freezable):
    label: str
    rendered: str
    _sources: dict[int, list[Markup]]
    _seen: set[str]
    def __init__(self) -> None: ...
    def add(self, src: str, priority: int = 1) -> None: ...
    def freeze(self, value: tuple[Markup, ...] | None = None) -> tuple[Markup, ...]: ...
    @property
    def sources(self) -> tuple[Markup, ...] | None: ...
