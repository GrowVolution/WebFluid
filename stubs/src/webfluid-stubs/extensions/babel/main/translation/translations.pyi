from collections.abc import Callable, Coroutine
from typing import Any

from webfluid.extensions.babel.main.main import Babel
from webfluid.extensions.babel.main.translation.domains import Domains

_Forms = dict[str, dict[str, str]]
_Translations = Callable[[], dict[str, dict[str, _Forms]]]


async def _load_translations(babel: Babel, domains: Domains) -> None: ...


class Translations:
    _update_tasks: list[Coroutine[Any, Any, None]]
    _update_blocked: bool
    _update_disabled: bool
    def __init__(self, update_disabled: bool) -> None: ...
    async def startup_hook(self, babel: Babel, domains: Domains) -> None: ...
    def update_translations(self, domain: str, translations: _Translations) -> None: ...
    async def _update_translations(self) -> None: ...
