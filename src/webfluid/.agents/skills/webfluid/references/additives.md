# Additives and extensions — the modularity story

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `25-39` **Which one**
- `40-403` **Additives**
  - `66-134` The manifest
    - `99-134` `requires.packages` — only what nothing else already brings
  - `135-173` The additive object
  - `174-196` Handlers and rendering
  - `197-232` Local lifecycle hooks
  - `233-252` Enabling
  - `253-268` The four rules
  - `269-316` Contracts: events and queries
    - `305-316` Contract design rules
  - `317-359` Base Additives
  - `360-388` `install()` and `configure()`
  - `389-403` Packaging checklist
- `404-481` **Extensions (`FluidExtension`)**
  - `457-481` What `expand_fluid` may do
<!-- /index -->

## Which one

| You want to ship…                                      | Use          |
|--------------------------------------------------------|--------------|
| Routes, templates, static files, a frontend            | **Additive** |
| A feature a project toggles per app config             | **Additive** |
| Something installed into `additives/`                  | **Additive** |
| A service other code calls (`db`, `mail`, `cache`)     | Extension    |
| Jinja globals or filters                               | Extension    |
| A `wf <name> …` command group                          | Extension    |
| Behaviour that must exist before routes are registered | Extension    |
| Something distributed and installed with `pip`         | Extension    |

---

# Additives

A self-contained sub-app: its own routers, templates, static files, frontend, request lifecycle and
manifest, mounted under its own URL prefix. `wf create additive <id>` generates all of it.

```text
additives/portal/
├── __init__.py        # exposes `additive: Additive`   (mandatory)
├── manifest.json      # id, version, type, frontend    (mandatory)
├── config.py          # @register_config, optional `setup` for wf create app
├── api/               # JSON routes -> /portal/api
├── app/               # HTML routes -> /portal
├── models/ schemas/ services/ events/ utils/
├── static/            # served at /portal/static
├── templates/         # namespaced under "portal/"
├── extract/           # files the HOST app should own
└── frontend/          # optional Vite workspace
```

Three hard requirements enforced by the constructor:

1. **The package must live under `additives.`** — otherwise `AdditiveException`.
2. **`manifest.json` must exist and validate.**
3. **The package must expose `additive`**, an `Additive` instance — `register_additives` logs an
   error and skips the package otherwise.

## The manifest

```json
{
  "id": "portal",
  "version": "1.0.0",
  "type": "default",
  "frontend": { "type": "none" },
  "name": "Portal",
  "description": "Customer portal",
  "authors": [{ "name": "Pierre", "email": "pierre@example.org" }],
  "requires": {
    "wf": ">=1.0.0b2",
    "additives": { "core": ">=1.0.0" },
    "packages": ["stripe"]
  }
}
```

| Field      | Required | Rules                                                                                                      |
|------------|----------|------------------------------------------------------------------------------------------------------------|
| `id`       | yes      | Must survive `safe_string()` — `[a-zA-Z0-9_-]` only. Cannot be `fluid`                                     |
| `version`  | yes      | 1–3 numbers, each 0–999, optional stage `a`/`b`/`rc` with build 1–9. No epoch, dev, post or local segments |
| `type`     | yes      | `"default"` or `"base"`                                                                                    |
| `frontend` | yes      | Same shape as `APP_FRONTEND`. A `base` **must** use `{"type": "none"}`                                     |
| `requires` | no       | `wf` (framework specifier), `additives` (map or list), `packages` (pip requirements)                       |

The **`id` is the public identity**: URL prefix (`_` → `-`), template namespace, static mount,
config-file switch, and the prefix `unique_name()` applies to contracts.

`requires.wf` and `requires.additives` are checked **at enable**; `packages` at `install()`. A
missing or mismatching Additive raises `AdditiveException`. A missing `wf` key only logs a warning.

### `requires.packages` — only what nothing else already brings

`packages` is not a dependency declaration that a resolver reconciles. `install_packages` runs
`pip install --upgrade <name>` once per entry, unconditionally, for the Additive and for its base,
after every Additive further down the chain has already installed its own. A name that something
else already provides is therefore not merely redundant — it is an unpinned upgrade of a package
that is already in the environment and working.

Before adding a line, check the three places a package can already come from:

1. **The framework's own dependencies.** WebFluid installs `fastapi`, `jinja2`, `babel`,
   `sqlalchemy`, `alembic`, `psycopg`, `pymysql`, `aiomysql`, `aiosqlite`, `redis`, `uvicorn`,
   `httpx`, `requests`, `websockets`, `asgiref`, `slowapi`, `limits`, `packaging`,
   `python-multipart`, `apscheduler`, `aiosmtplib`, `gitpython`, `frozendict`, `selectolax`,
   `pytz`, `argon2_cffi`, `itsdangerous`, `authlib`, `pyjwt`, `typer`, `tqdm` and `questionary`.
   Read the installed distribution rather than trusting that list to stay current:

   ```bash
   python -c "from importlib.metadata import requires; print(requires('webfluid'))"
   ```

   Several are version-pinned by the framework — `redis>=7.3.0`, `slowapi>=0.1.9`, `limits>=5.8.0`,
   `packaging>=26.0`. Listing one and letting `--upgrade` move it is how an Additive breaks the host
   application it was installed into.
2. **An Additive you require.** `requires.additives` is resolved and installed *first*, so anything
   in that Additive's own `packages` is already present. Do not repeat it — if you need it, you
   already depend on the Additive that brings it.
3. **Your base.** A `default` Additive extending a `base` inherits the base's packages, installed
   immediately before its own.

What belongs in `packages` is what only *this* Additive needs and nothing above it in the chain
provides: a payment SDK, a PDF renderer, a vendor client. If you genuinely need a different version
of something the framework ships, that is not a `packages` entry — say so in the Additive's
description and let the host decide, because `--upgrade` would otherwise change it silently at
install time.

## The additive object

```python
# additives/portal/__init__.py
from webfluid import Additive

additive = Additive(__name__, required_extensions=["sqlalchemy", "events"])


@additive.before_enable
def before_enable(fluid):
    from .app import index
    additive.app.get("/")(index)

    from .api import v1
    additive.api.include_router(v1)

    from .events import contracts  # noqa: importing registers them
```

`Additive(import_name, base=None, required_extensions=None)`. `required_extensions` are lowercase
names checked against `EXT_<NAME>` at enable time; a missing one raises
`RuntimeError: Extension '<name>' is not enabled.` A base's list is merged into the child's.

> **Register routes inside `before_enable`, not at module level.** The framework includes the three
> routers into the app the moment the Additive is enabled — anything attached after that point is
> never mounted. `before_enable` is also already inside the running event loop, which is what event,
> query and scheduler registration needs.

| Router         | Prefix | Default response | Mounted at  |
|----------------|--------|------------------|-------------|
| `additive.app` | —      | `HTMLResponse`   | `/<id>`     |
| `additive.api` | `/api` | JSON             | `/<id>/api` |
| `additive.ws`  | `/ws`  | —                | `/<id>/ws`  |

(For a **base** all three are created without prefixes, because the child supplies them.) They are
`Router` instances — `APIRouter` subclasses that attribute every endpoint's log lines to the Additive
and support `http_middleware`.

## Handlers and rendering

```python
# additives/portal/app/index.py
async def handle_request():
    from .. import additive
    return await additive.render("index.html")
```

> **Import the additive object lazily inside the handler.** The package `__init__` imports the
> handler modules from `before_enable`, so a top-level `from .. import additive` in a handler module
> is a circular import.

`additive.render(template, **ctx)` runs the Additive's own context processors, prefixes the name
with the Additive's id, and delegates to `FluidContext.current().fluid.render(...)`. So
`additive.render("index.html")` resolves `additives/portal/templates/index.html`. It needs a
`FluidContext` — rendering from a scheduled job means building one yourself.

The Additive's Jinja context always carries `id` and a scoped `url_for`: it runs the endpoint name
through `unique_name()` first, so reverse-URL lookups never collide, and falls back to the plain
name when nothing matches the scoped one. Write `url_for("index")` for your own route and
`url_for("static")` for a host-app one — the same call covers both, on and off request.

## Local lifecycle hooks

```python
@additive.context_processor
def defaults(): return {"section": "portal"}

@additive.before_request
def guard(): ...              # return a response to short-circuit

@additive.after_request
async def shape(result): return result

@additive.before_enable
def before_enable(fluid): ...  # exactly one argument: fluid

@additive.after_enable
def after_enable(): ...        # no arguments
```

All of these are **scoped to the Additive's own routes**, not the whole app.

> **`additive.after_request` does not receive a `Response`.** It runs inside the router's endpoint
> wrapper, before FastAPI serialises anything, so it receives — and must return — whatever your
> handler returned: a dict, a pydantic model, a string. `fluid.after_request`, in the ASGI
> middleware, does receive a real `Response`. Same name, different altitude.

`http_middleware` wraps every route of one router, and the chain is built once, not per request:

```python
@additive.api.http_middleware
def timed(call_next):
    async def wrapper(*args, **kwargs):
        return await call_next(*args, **kwargs)
    return wrapper
```

## Enabling

Two switches, both required:

```ini
[features]
WF_ADDITIVES = 1

[additives]
portal = 1
```

The key is the manifest **`id`**. `register_additives` runs as a startup hook and, per Additive:
`check_enable()` (a base raises here) → `manifest.check_requirements()` → fold in the base if any →
frontend → jinja context and template loader → include the three routers under `/<prefix>` → mount
`static/` at `/<prefix>/static` under the route name `<id>_static`.

`before_enable` hooks run before that body, `after_enable` after. Failures are caught and logged per
Additive — one broken Additive does not stop the app.

## The four rules

1. **One feature per Additive.** If two always ship together and neither works alone, they are one
   Additive — or one base plus one child.
2. **Never import another Additive's Python modules.** An import welds the two together: you cannot
   ship one without the other, disabling one breaks the other, and the enable order becomes
   load-bearing. The only thing allowed to cross an Additive boundary is a **string**.
3. **Prefix everything with the id** — config keys (`<ID>_*` manually), cache keys, event and query
   names (`additive.unique_name()`).
4. **Reach batteries through `webfluid.core.ext`**, exactly as the main app does. An Additive shares
   the runtime: same database, same cache, same event manager, no wiring.

Importing the main app's modules (`fluid.models`, `fluid.services`) is a different case — it couples
the Additive to *this* project, which is fine for a project-local Additive and fatal for a
distributed one. If you intend to publish it, do not import `fluid.*` either.

## Contracts: events and queries

`additive.unique_name(name)` prefixes with the Additive's id, giving every contract a stable address.

```python
# additives/portal/events/contracts.py — the producer
from webfluid.core.ext import db, events
from .. import additive


@events.query(additive.unique_name("entry_count"))     # served as "portal_entry_count"
async def entry_count(_): ...


events.create_signal(additive.unique_name("entry:created"), internal=False)
```

```python
# additives/dashboard/events/listeners.py — the consumer
from webfluid.core.ext import events

PORTAL = "portal"          # declared under requires.additives in our manifest


async def overview():
    return await events.request(f"{PORTAL}_entry_count")


@events.event(f"{PORTAL}_entry:created", internal=False)
async def on_created(data): ...
```

Because the consumer depends on `portal` by id and version in its manifest, the framework guarantees
`portal` is present before either is enabled — so the string address is safe and no Python import
ever crosses the boundary.

### Contract design rules

- **Version contract names when you change their shape.** `portal_entry_count` stays,
  `portal_entry_count_v2` is added. A consumer pinned to an older version must keep working, and
  there is no type checking across the boundary.
- **Pass plain JSON-shaped data** — dicts, lists, strings, numbers. **Never an ORM instance**: it is
  detached, its relationships raise, and the consumer would need your models to do anything with it.
- **Query when the caller needs an answer, event when it does not.** `singleton=True` (the default)
  means exactly one Additive may serve it; `singleton=False` fans out and the caller gets a list.
- **Handle a missing producer.** `events.request` raises `ValueError` for an unknown name, so an
  optional dependency needs `events.has_query(name)` or a `try`/`except`.

## Base Additives

A foundation meant to be **extended**, not run: `"type": "base"`, no frontend, never listed in
`[additives]`, folded into exactly one default Additive at enable time.

```python
from webfluid.utils.additives import import_base

additive = Additive(__name__, import_base("core"), required_extensions=["events"])
```

> **Resolve the base with `import_base("<id>")`, never a direct Python import.** It walks the
> installed bases in `additives/`, matches the manifest id, imports the package and verifies it is
> actually a base. A direct import hardcodes the directory name.

`import_base` returns `None` when the base is not installed, and `Additive(__name__, None)` is a
plain Additive with no base — so declare the dependency in `requires.additives` to make enabling
fail loudly.

What extension does, when the child is enabled: both manifests' requirements are checked; the base's
routers are included into the child's (so `/about` becomes `/portal/about`); `base.parent = child`,
`base.prefix = child.prefix`, `base.jinja_context["id"] = child.id`; the base's templates join as a
`ChoiceLoader` (child first) under the **child's** id namespace; base hooks run after the child's.

Consequences: the base's `render` forwards to the parent, so a template the child overrides wins;
`unique_name()` on the base delegates to the parent, so two projects extending the same base do not
collide; reverse URLs line up through the child's id.

| Constraint                                                   | Enforced by                   |
|--------------------------------------------------------------|-------------------------------|
| A base may not have a frontend                               | `ManifestError` at validation |
| A base may not extend another base                           | `AdditiveException`           |
| A default Additive may only extend a **base**                | `AdditiveException`           |
| A base may not be enabled directly                           | `AdditiveException`           |
| A base may be extended by **exactly one** Additive at a time | `AdditiveException`           |

> The one-parent rule surprises people. If two enabled Additives both extend the same base, enabling
> the second one fails. **A base is a foundation for a single feature, not a shared service** — if
> you need a shared service, write an extension.

Discovery: `installed_additives(root)`, `installed_bases(root)`, `import_base(id)` from
`webfluid.utils.additives`. Results are cached per package path; pass `cache=False` for a fresh scan.

## `install()` and `configure()`

`install()` runs on `wf ocean install` and — in debug with `DEV_AUTO_INSTALL=1` — on every
registration:

1. Resolve the Additives this manifest requires; pull missing ones from the Ocean, recursively.
2. Copy everything in `extract/` into the main app. **Existing files are never overwritten.**
3. Install the manifest's `packages` with pip.

Use `extract/` for files the host app is meant to own and edit — a page template it should
customise, a stylesheet it should extend. Everything the Additive owns stays in its own `templates/`
and `static/`, where an upgrade can replace it.

`configure()` lets an Additive contribute questions to `wf create app`:

```python
# additives/portal/config.py
setup = {
    "PORTAL_API_KEY": {"type": "password", "message": "Portal API key:"},
    "PORTAL_REGION": {"type": "select", "message": "Region:",
                      "kwargs": {"choices": ["eu", "us"], "default": "eu"}},
    "PORTAL_ENABLED": {"type": "auto", "value": "1"}
}
```

`type` is one of `text`, `password`, `select`, `checkbox`, `confirm`, `auto`. `message` is required
except for `auto`, which needs `value`. Answers land in a config section named after the id. A base
is configured before its child.

## Packaging checklist

- [ ] `manifest.json` — correct `id`, real `version`, `requires.wf` set, dependencies declared
- [ ] No import of another Additive or of `fluid.*`
- [ ] Every contract name goes through `unique_name()`
- [ ] Every config key prefixed with the id
- [ ] `required_extensions` lists what the code actually uses
- [ ] `requires.packages` holds nothing the framework, a required Additive or your base already
      installs
- [ ] `.gitignore` present — it decides what ships
- [ ] `extract/` holds only what the host should own
- [ ] A license

---

# Extensions (`FluidExtension`)

A Python **distribution** advertising itself through the `webfluid.extensions` entry-point group.

```toml
[project.entry-points."webfluid.extensions"]
myext = "extension.main:MyExtension"
```

The group name is exactly `webfluid.extensions`; the entry-point **name** becomes the CLI
sub-command (`wf myext …`); the target must be a `FluidExtension` subclass (anything else is skipped
with a warning).

```python
from webfluid.extensions import FluidExtension
import typer


class MyExtension(FluidExtension):
    _cli = typer.Typer(help="My extension.")

    def __init__(self, fluid=None, *_, **__):
        self._foo = "default"
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._foo = fluid.config.get("MYEXT_FOO", self._foo)
        fluid.jinja_env.globals["my_ext"] = self._my_util
        fluid.startup_hook(self._warm_up)

    @staticmethod
    @_cli.command()
    def hello(name: str):
        typer.secho(f"Hello {name} :)", fg=typer.colors.GREEN)
```

Three rules follow from the base class:

1. **`expand_fluid(fluid, *args, **kwargs)` is the only required override.**
2. **Constructing with a `fluid` calls `expand_fluid` immediately** — keep the parent signature so
   both `MyExtension(app)` and `MyExtension().expand_fluid(app)` work.
3. **A `_cli` class attribute becomes a `wf` sub-command.** Commands must be `staticmethod`s — they
   run without an application.

**Set every instance attribute in `__init__` before calling `super().__init__(fluid)`**, because the
parent may call `expand_fluid` immediately and `expand_fluid` usually reads those attributes as its
defaults. Your keys are not in `DefaultConfig`, so this is the one place `fluid.config.get(key,
default)` is correct — prefix them `MYEXT_*`.

`Delegated("_sync.send")` is a descriptor that raises a clear `FrameworkException` when
`expand_fluid` has not run yet, instead of `AttributeError: NoneType`. Use it for sub-objects you
build lazily in `expand_fluid`.

### What `expand_fluid` may do

`fluid.config[...]`, `fluid.jinja_env.globals/filters/add_extension`, `startup_hook` /
`shutdown_hook`, `context_processor`, `before_request` / `after_request`, `add_source`,
`add_template_loader`, `fluid.websocket(path)(handler)`, `fluid.static_prefixes.add(prefix)`.

`add_source`, `add_template_loader` and `static_prefixes` are frozen in the `_prepare` startup hook —
call them during `expand_fluid`, not later.

Guard on other batteries the way `JWTManager` does:

```python
from webfluid.core.constants import EXT_SCHEDULING
from webfluid.exceptions import FrameworkException

if not EXT_SCHEDULING:
    raise FrameworkException("EXT_SCHEDULING is required for MyExtension to work.")
```

Those constants are read once at import time; use `webfluid.utils.enabled("EXT_CACHE")` for a
dynamic check.

**Do not instantiate a built-in battery yourself.** SQLAlchemy raises `FrameworkException` on a
second `expand_fluid`, and the others assume a single process-wide instance. Import from
`webfluid.core.ext`.
