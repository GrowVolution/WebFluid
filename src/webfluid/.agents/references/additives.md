# Additives and extensions — the modularity story

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `27-41` **Which one**
- `42-491` **Additives**
  - `68-136` The manifest
    - `101-136` `requires.packages` — only what nothing else already brings
  - `137-176` The additive object
  - `177-199` Handlers and rendering
  - `200-251` Local lifecycle hooks
  - `252-271` Enabling
  - `272-287` The four rules
  - `288-335` Contracts: events and queries
    - `324-335` Contract design rules
  - `336-380` Base Additives
  - `381-409` `install()` and `configure()`
  - `410-471` Documenting an Additive for people and agents
    - `446-471` References point down, never up
  - `472-491` Packaging checklist
- `492-581` **Extensions (`FluidExtension`)**
  - `557-581` What `expand_fluid` may do
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

    from .api import setup_v1, health
    additive.api.get("/health")(health)
    setup_v1(additive)

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

**An exception in `before_enable` or `after_enable` fails the Additive's registration.** The error
is logged against the Additive and the others still register. Registration is not transactional:
earlier side effects remain, and a failed `after_enable` can leave mounted routes. Do not treat
the registration log as a guarantee that the application or dependent modules stopped.

1. Run migrations before serving requests. Security-critical initialization, such as loading
   token revocations, must propagate failures rather than silently accepting an empty state.
2. Keep assembly separate from optional database maintenance. Optional work can run as a one-shot
   scheduler job or handle a specific database error with an actionable log. Do not apply that
   recovery to authorization, revocation or other security prerequisites.
3. Use the async executor in enable hooks; a sync executor blocks the boot loop.

Startup hooks are closed by the time an Additive enables: `fluid.startup_hook(...)` from inside an
enable hook raises `RuntimeError`. The scheduler is the place for work that must follow the boot —
list `scheduling` in `required_extensions` when you use it.

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
`root` must be the `additives` package directory: when it does not exist yet, both answer `[]`; a file of
that name, or a directory with another name, raises `ValueError`.

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

## Documenting an Additive for people and agents

An Additive is reused by people who decide whether to install it and by agents who wire it into an
application. Each audience gets its own file, and none of them repeats another:

| File               | Reader   | Holds                                                                                               |
|--------------------|----------|-----------------------------------------------------------------------------------------------------|
| `README.md`        | people   | The landing page: why the Additive exists, what it gives a project, install, license               |
| `DOCS.md`          | people   | The guide a person reads before answering for the Additive: concepts, flows, every setting and what it changes, security model, operation, troubleshooting |
| `CHANGELOG.md`     | people   | What changed per version, in plain language, with what an upgrade requires                          |
| `CONTRACT.md`      | agents   | The complete integration surface: routes, signals, queries provided and consumed, config, errors    |
| `.agents/SKILL.md` | agents   | When to use the Additive, the rules that keep an integration correct, recipes, and where to look    |

`DOCS.md` explains; it does not enumerate. It may name a route, a signal or an error code to make a
flow understandable, and points into `CONTRACT.md` for the exact shapes rather than copying them, so
the two never drift apart. An SDK carries the same set next to its own `pubspec.yaml` or
`pyproject.toml`.

`CONTRACT.md` is the reference an agent loads in parts, so it states payloads, answers and error
codes exactly and describes an Additive **only through what it provides and what it requires** —
never through the applications that happen to use it. `.agents/SKILL.md` stays short: frontmatter
with a `name` and a `description` that says when to load it, then the decisions an agent gets wrong
without it. It does not copy the contract; it links into it by line range:

```markdown
## Contract map

<!-- index ../CONTRACT.md -->
<!-- /index -->
```

`wf agents index` fills every `<!-- index -->` block below the current directory — the file's own
sections, or the sections of the file a block names — and leaves everything else untouched. Run it
after editing either file; `wf agents index --check` changes nothing and exits with `1` when a range
is stale, which makes it a fitting CI step.

### References point down, never up

Every package documents itself as if nothing above it existed. Its Markdown — `README.md`,
`CHANGELOG.md`, `CONTRACT.md`, `.agents/SKILL.md` and any reference file — may name the framework,
its own dependencies (the `requires` of its manifest, transitively) and the optional contracts it
consumes. It never names a package, SDK or application that depends on it — and `DOCS.md` is no
exception, however natural an example from a real consumer would read. The same holds for
extensions and for SDKs, whose dependencies are their `pubspec.yaml` or `pyproject.toml`.

| Situation                                          | Write                                                                 | Not                                                         |
|----------------------------------------------------|-----------------------------------------------------------------------|-------------------------------------------------------------|
| A feature moved into a lower package               | Its CHANGELOG describes the feature and the upgrade on its own terms  | "moved here from `users`", "the users SDK now sends …"      |
| The consumer had to change because of it           | The consumer's CHANGELOG says so and names the lower package          | the lower package explaining its consumers' upgrade         |
| An example payload, id, header or class            | A neutral name: `my-app`, `shop:order`, `myapp/1.0.0 (android; …)`    | the name of a real consumer                                 |
| A collector or extension point                     | The owner documents the query; each contributor documents its answer  | the owner listing who contributes                           |
| A requirement only some consumer has               | That consumer's README or SKILL, e.g. a platform setting               | the lower package's setup guide                             |
| Two packages must stay aligned                     | The higher one follows the lower one's CHANGELOG                      | the lower one promising to follow its consumers             |

A lower package that seems to need a sentence about its consumers is usually missing a neutral
concept: a role (`host`, `peer`), a generic consumer ("any route", "an Additive that integrates
it"), or an extension point the consumers implement. Name that concept instead.

The rule reaches into code where a package answers another package's collector: contribute only to
collectors of packages you require. A collector every contributor should reach belongs to the lowest
package they all require, so that no package has to answer a query of one built on top of it.

## Packaging checklist

- [ ] `manifest.json` — correct `id`, real `version`, `requires.wf` set, dependencies declared
- [ ] No import of another Additive or of `fluid.*`
- [ ] Every contract name goes through `unique_name()`
- [ ] Every config key prefixed with the id
- [ ] `required_extensions` lists what the code actually uses
- [ ] Migrations precede serving traffic; security-critical initialization propagates errors;
      only optional work is deferred, and enable hooks use the async executor
- [ ] `requires.packages` holds nothing the framework, a required Additive or your base already
      installs
- [ ] `.gitignore` present — it decides what ships
- [ ] `extract/` holds only what the host should own
- [ ] `README.md`, `DOCS.md`, `CONTRACT.md` and `.agents/SKILL.md` present, indexes current
      (`wf agents index --check`)
- [ ] No Markdown names a package or app that depends on this one
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

`FluidExtension` is an abstract base class and `expand_fluid` is its abstract method: a subclass
that does not implement it cannot be instantiated at all — `TypeError` at construction, before any
`fluid` is passed. The same holds for the framework's other extension points: a cache backend
implements all eight methods of `BaseCache` (`set`, `get`, `delete`, `clear` and their `a*` twins),
and an executor implements `exec`, `insert`, `delete` and `flush` of the executor base.

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

The error comes from `raise_unexpanded()`, a classmethod of `FluidExtension`: it raises
`FrameworkException(cls._unexpanded.format(instance=cls.__name__))`. Call it yourself to guard a method
that needs the expanded state (`if self._fluid is None: MyExtension.raise_unexpanded()`), and override the
class attribute `_unexpanded` — default `"{instance}.expand_fluid() has never been called."` — to change
the message for every delegated attribute at once.

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
