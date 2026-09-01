from collections.abc import Callable
from pathlib import Path
from typing import Any

from webfluid.extensions.babel.domain import Domain


class Domains:
    store: dict[str, Domain]
    default_domain: Domain
    def __init__(self, default_domain: Domain | None) -> None: ...
    def register_domain(self, name: str, package: Path | None = None) -> None: ...
    def domain_context(self, domain: str) -> Callable[..., Any]: ...
    @property
    def current_domain(self) -> Domain: ...
