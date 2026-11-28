# Code style and package architecture

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `30-106` **Package architecture**
  - `49-80` Services are classes
  - `81-100` Packages that grow
  - `101-106` Public API
- `107-143` **Imports**
- `144-201` **Module layout**
  - `192-201` Class body
- `202-208` **Schemas and exceptions**
- `209-220` **Formatting**
- `221-229` **Checklist before you hand over**
<!-- /index -->

WebFluid code is written by agents and answered for by people. One shape everywhere is what makes
both work: an agent reads a module it has never seen with the fewest tokens because it knows where
each kind of statement sits, and a reviewer recognises a wrong change because it breaks a shape they
know. This file is binding for the framework, for every extension and for every Additive — read it
before you create or restructure a package, and always before you build an Additive or an extension
that is meant to be published on Ocean. Code that follows it reads like the rest of the ecosystem;
code that does not is the first thing a maintainer sends back.

The rules describe how existing WebFluid code already looks. When a file you edit deviates, bring
the parts you touch into line — do not restyle unrelated files in the same change.

## Package architecture

An Additive or an application package uses these modules. Create only the ones the package needs.

| Module          | Holds                                                                                                     |
|-----------------|-----------------------------------------------------------------------------------------------------------|
| `__init__.py`   | The `additive` object and its lifecycle hooks — or, for any other package, the bundling of its submodules |
| `config.py`     | The config class, the secret gate, the `setup` questions of `wf create app`                               |
| `api/`          | JSON handlers, one module per resource; `api/v1/__init__.py` assembles the router                         |
| `app/`          | HTML handlers                                                                                             |
| `events/`       | Signal, event and query handlers, registered from a hook                                                  |
| `models/`       | `db.Model` subclasses, association tables and their shared bind setup in `__init__.py`                                                                      |
| `schemas/`      | Pydantic models — nothing else, and no Pydantic model anywhere else                                       |
| `services/`     | Business logic: one service class per module, exported from `services/__init__.py`                        |
| `utils/`        | Stateless helpers that need neither the database nor the request                                          |
| `exceptions.py` | Every exception class of the package                                                                      |
| `jobs.py`       | Scheduled jobs that stand on their own                                                                    |
| `i18n/`         | `default.json` and the translation resolver                                                               |

### Services are classes

Every service is a class named `<Domain>Service` in its own module under `services/`, and the
package exports it:

```python
from .media import MediaService
from .rooms import RoomService

__all__ = ["MediaService", "RoomService"]
```

- Callers import the service from the package — `from ..services import RoomService` — never a
  function or a module out of it. Inside `services/`, siblings import each other's module directly
  (`from .rooms import RoomService`).
- Methods are `@staticmethod`, or `@classmethod` when they call other members through `cls`.
  Process-wide settings live on the class and are filled by a `setup()` or `configure()`
  classmethod from a lifecycle hook.
- Constants another module needs are class attributes (`PoolService.EVERYONE`). Constants only the
  module uses stay at module level.
- A private helper that needs neither the class nor its state is a module-level `_function`, not a
  private static method.
- A name with a leading underscore never crosses a module boundary. When two modules need the same
  helper, it becomes public — on the service, or in a package-internal module.
- A query helper that belongs to an entity lives on the model (`ChatEvent.alive()`), not in a
  service.
- Utilities that every service may use go to `utils/`; a service never imports a function from
  another service's module.
- A framework or extension package may load its services lazily with a module `__getattr__` and
  `__all__` (see `webfluid.extensions.security.services`); an Additive's `services/__init__.py`
  imports them eagerly.

### Packages that grow

A module that passes roughly 400–500 lines, or that holds more than one responsibility, becomes a
package of smaller modules that still acts as one unit to its callers:

- **A large service** becomes `services/<name>/` with one module per responsibility and a
  `service.py` that composes them: `class AccountService(AccountAddresses, AccountMerchants,
  AccountOrganisations)`. The parts call each other through `cls`, so callers keep using
  `AccountService.<method>` and nothing outside the package changes. Helpers several parts share go
  to a package-internal `common.py`, without a leading underscore.
- **A large handler or utility module** becomes a package whose `__init__.py` re-exports the
  public names through `__all__` (`api/v1/two_fa/` with `status.py`, `totp.py`, `webauthn.py`,
  `backup.py`, `mobile.py`).
- **A large schema module** first separates its groups of models with three blank lines; once that
  stops being readable, `schemas/v1.py` becomes `schemas/v1/` with one module per group and an
  `__init__.py` that re-exports every model through `__all__`.

The framework does the same with a delegating class: `Fluid` hands routing, rate limits and the
server to `Routes`, `Limiter` and `Server`; `UserService` composes its gates.

### Public API

The public API of a distribution is what the `__all__` of its `__init__.py` files declares. An
`__init__.py` bundles its submodules and defines only what the whole package shares, for example a
`Path(__file__).parent` every module would otherwise compute. Leaf modules carry no `__all__`.

## Imports

```python
from webfluid.core.ext import db, events
from webfluid.utils.logging import factory as log_factory
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING, Optional
import hashlib, json, re

from ..models import ChatEvent, ChatRoom
from ..utils import b64, now
from .chat import ChatService

if TYPE_CHECKING:
    from webfluid.extensions.security.models import User
```

1. External imports open the file at line 1: the framework (`webfluid`) first, then third-party
   libraries, then the standard library, each group sorted by module — and all plain `import x`
   statements in **one** line at the end of the block (`import hashlib, json, re`).
2. One blank line, then the imports of the package the module belongs to. Without external imports
   they start at line 1.
3. Within the package block, relative imports come before absolute ones, parents (`..`) before
   siblings (`.`).
4. One `from` line per module. Never two lines importing from the same module.
5. `if TYPE_CHECKING:` follows the imports after one blank line and may hold several lines.
6. **Additives import their own modules relatively**, always — it keeps the no-cross-import
   contract visible: an absolute `additives.` import in an Additive is always a mistake.
   Distributions on PyPI (the framework, extensions) import absolutely (`wf_peering.services`),
   except inside a package that deliberately acts as one monolithic module (`core.fluid`,
   `core.additive`, `extensions.security.services.user`), where relative imports are fine.
7. Import inside a function only to break a real import cycle — `from .. import additive` in an
   Additive — or to load something lazily that a code path rarely needs. Put such an import into the
   branch that needs it, not at the top of the function.

## Module layout

```python
from datetime import timedelta
import re

from ..models import PoolEntry

SUBJECT_LIMIT = 50
SWEEP_BATCH = 500
CHECK_INTERVAL = timedelta(days=1)

_settings = { "idle": 30 }

CONTEXT = "users-pool-v1"
SUBJECT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}:[A-Za-z0-9_.:-]{1,95}$")


def _now() -> datetime:
    ...


async def entries(account: str) -> dict:
    ...


class PoolService:
    ...
```

- After the imports, one blank line, then the variables. A file without imports starts with one
  blank line; a file with neither imports nor variables starts with two blank lines before its first
  function or class.
- Variables in this order, each group separated by one blank line:
  1. **Tunables** — constants a developer adjusts but an operator does not reach through
     `fluid.config`: hard limits, batch sizes, intervals, curves, resource allocation.
  2. **Private variables** (`_name`).
  3. **Everything else** a caller may import.

  From four or five entries on, separate logical groups inside one category with a blank line.
- Two blank lines, then the functions: private (`_name`) before public, undecorated before
  decorated within each.
- Then the classes in the same order: private before public, undecorated before decorated.
- Two blank lines between top-level functions and classes, one between methods.
- An order is only broken where Python needs it: a variable that calls a function follows that
  function; a subclass follows its base; imports that must run after an assignment
  (`app_router = APIRouter()` before the handlers that use it) stay where they are.

### Class body

1. Class variables and constants, in the module order above, without a leading blank line.
2. Dunder methods, `__init__` first.
3. Private methods, then private decorated ones (`@classmethod`, `@contextmanager`, …).
4. Public methods, then public decorated ones (`@property`, `@classmethod`, `@staticmethod`, …).

One blank line between methods. Records — Pydantic and SQLAlchemy models, dataclasses, enums,
`NamedTuple`s — keep their fields in declaration order, because the order is part of their meaning.

## Schemas and exceptions

- Every Pydantic model lives in `schemas/` — request bodies too. `schemas/v1.py` groups related models
  together; from a medium size on, three blank lines separate the groups.
- Every exception class lives in the package's `exceptions.py`. Code raises and catches it from there
  — never as an attribute of the module that happens to raise it.

## Formatting

- Lines end at 120 characters. A continuation line aligns with the opening bracket.
- No comments and no docstrings. Explain decisions in the commit message and the package's
  Markdown.
- Names say what a thing is: a service ends in `Service`, a composing part names its responsibility
  (`AccountAddresses`), a helper says what it returns (`other_members`, `bump_revision`). Abbreviate
  only what the domain abbreviates (`olm`, `jwt`).
- Routes are English: the path (`/imprint`, `/privacy`, `/api/v1/shipments`) and the route name
  `url_for` reverses (`imprint_request`) — also on a site whose pages are written in another
  language. The page's language comes from the locale, never from its URL.

## Checklist before you hand over

- [ ] Every new or changed module follows the import block and the module layout above
- [ ] Services are `<Domain>Service` classes exported from `services/__init__.py`; nothing imports a
      `_private` name from another module
- [ ] No Pydantic model outside `schemas/`, no exception class outside `exceptions.py`
- [ ] No module beyond roughly 500 lines without a reason; a split keeps the old public names
- [ ] No function-local import without a cycle or a lazy-loading reason
- [ ] The package's tests pass and the application still boots with every Additive registered
