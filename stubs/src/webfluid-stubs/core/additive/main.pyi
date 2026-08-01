from collections.abc import Awaitable, Callable
from configparser import ConfigParser
from pathlib import Path
from typing import Any

from frozendict import frozendict

from webfluid import Fluid
from webfluid.core.additive.jinja import Jinja
from webfluid.core.additive.kind import BaseKind, FeatureKind
from webfluid.core.additive.manifest import Manifest
from webfluid.core.additive.router import Router
from webfluid.core.lifecycle import AdditiveLifecycle, RequestLifecycle
from webfluid.surface.frontend import Frontend
from webfluid.utils.core import Version

class Additive:
    name: str
    import_name: str
    root_path: Path
    manifest: Manifest
    id: str
    prefix: str
    version: Version
    is_base: bool
    required_extensions: list[str]
    base: Additive | None
    parent: Additive | None
    enable: Callable[[Fluid], Awaitable[None]]
    api: Router
    app: Router
    ws: Router
    frontend: Frontend | None
    _kind: BaseKind | FeatureKind
    _lifecycle: AdditiveLifecycle
    _request_lifecycle: RequestLifecycle
    _jinja: Jinja
    def __init__(
        self, import_name: str, base: Additive | None = None,
        required_extensions: list[str] | None = None
    ) -> None: ...
    def __repr__(self) -> str: ...
    def unique_name(self, name: str) -> str: ...
    def check_enable(self) -> None: ...
    def install(self, _seen: set[str] | None = None) -> None: ...
    def configure(self, config: ConfigParser) -> None: ...
    @property
    def before_enable(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    @property
    def after_enable(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    @property
    def before_request(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    @property
    def after_request(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    @property
    def context_processor(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    @property
    def jinja_context(self) -> dict[str, Any] | frozendict[str, Any]: ...
    @property
    def render(self) -> Callable[..., Awaitable[str]]: ...
