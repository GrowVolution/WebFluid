from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, AbstractAsyncContextManager
from typing import Any

import typer

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.babel.domain import Domain
from webfluid.extensions.babel.speaklater import LazyString
from webfluid.extensions.babel.babel.socket import Socket
from webfluid.extensions.babel.babel.translation import Translator


class Babel(FluidExtension):
    _cli: typer.Typer
    _translator: Translator | None
    _socket: Socket | None
    default_locale: str | None
    default_timezone: str | None
    supported_locales: tuple[str, ...] | None
    date_formats: Any
    gettext: Callable[..., str]
    ngettext: Callable[..., str]
    pgettext: Callable[..., str]
    npgettext: Callable[..., str]
    agettext: Callable[..., Awaitable[str]]
    angettext: Callable[..., Awaitable[str]]
    apgettext: Callable[..., Awaitable[str]]
    anpgettext: Callable[..., Awaitable[str]]
    lazy_gettext: Callable[..., LazyString]
    lazy_ngettext: Callable[..., LazyString]
    lazy_pgettext: Callable[..., LazyString]
    lazy_npgettext: Callable[..., LazyString]
    register_domain: Callable[..., None]
    domain_context: Callable[..., Callable[..., Any]]
    current_domain: Domain
    update_translations: Callable[..., None]
    locale_selector: Callable[..., Callable[..., Any]]
    timezone_selector: Callable[..., Callable[..., Any]]
    locale_selector_fn: Callable[..., Any] | None
    timezone_selector_fn: Callable[..., Any] | None
    force: Callable[..., AbstractContextManager[None]]
    aforce: Callable[..., AbstractAsyncContextManager[None]]
    def __init__(
        self, fluid: Fluid | None = None, default_domain: Domain | None = None
    ) -> None: ...
    def expand_fluid(self, fluid: Fluid, *_: Any, **kwargs: Any) -> None: ...
