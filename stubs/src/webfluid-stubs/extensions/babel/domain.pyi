from os import PathLike

from webfluid import Fluid
from webfluid.extensions.babel.translations import MergedTranslations

class Domain:
    dir: str | PathLike[str] | None
    domain: str
    cache: dict[str, MergedTranslations]
    def __init__(
        self, dir_path: str | PathLike[str] | None = None, domain: str = "messages"
    ) -> None: ...
    def get_translations_path(self, fluid: Fluid | None) -> PathLike[str] | str: ...
    def get_translations(self) -> MergedTranslations: ...
