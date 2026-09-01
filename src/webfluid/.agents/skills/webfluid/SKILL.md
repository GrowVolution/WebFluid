---
name: webfluid
description: Build and maintain applications on the WebFluid framework (the `webfluid` package, `Fluid`, `wf` CLI, Additives, `webfluid.core.ext` batteries). Use whenever a project contains main.py with prepare_fluid(), an app_configs/ directory, a fluid/ package, an additives/ tree or a manifest.json — or when the task mentions WebFluid, Fluid, Additives, Ocean, or the wf command. Use it even when the task looks like ordinary FastAPI, SQLAlchemy or Jinja work: inside a WebFluid project those libraries are wired by the framework, and the plain-library answer is usually the wrong one.
---

# Working with WebFluid

<!-- index -->
This file is short enough to read whole; the ranges are for coming back to one section. Every
`references/*.md` opens with an index of the same shape — read those first 30 lines, then only the
ranges the task needs.

- `39-59` **Orient before you write**
- `60-105` **The rules that keep generated code correct**
- `106-190` **The shapes to generate**
- `191-208` **Task → route**
- `209-218` **Verify your work**
- `219-251` **Pull deeper detail live**
- `252-265` **References**
<!-- /index -->

WebFluid is a fullstack Python application runtime on top of FastAPI. `Fluid` is a `FastAPI`
subclass, so every FastAPI idiom still applies; on top of it the framework owns configuration,
logging, the event loop, the frontend build, the migration environment and a module registry.

Mental model: **FastAPI for the routes, Flask-shaped ergonomics for the app object, and a runtime
that owns the process.**

|           |                                                                                          |
|-----------|------------------------------------------------------------------------------------------|
| Python    | 3.14+ (hard requirement)                                                                 |
| App class | `webfluid.Fluid`                                                                         |
| Run       | `wf run <app>` — **never** `uvicorn main:app`                                            |
| Templates | Jinja2, **async**, autoescape **on** (html/xml suffixes + `render_string`)               |
| ORM       | SQLAlchemy 2.x, sync **and** async sessions                                              |
| Batteries | `from webfluid.core.ext import scheduler, db, babel, security, events, cache, mail, jwt` |
| Live docs | <https://docs.webfluid.dev/llms.txt>                                                     |

## Orient before you write

Almost every WebFluid mistake comes from assuming a feature is available. Nothing is on by default.
Read these four things first — it costs one tool call each and settles what your code may use:

| Read                        | Tells you                                                                          |
|-----------------------------|------------------------------------------------------------------------------------|
| `app_configs/*.ini`         | Per app: the `EXT_*`, `WF_*` and `[additives]` switches — and every secret it uses |
| `fluid/config.py`           | The committed, non-secret settings: `APP_CONFIG`, `APP_FRONTEND`, binds, own keys  |
| `main.py`                   | The `prepare_fluid()` factory: which routers, hooks and extensions are wired       |
| `additives/*/manifest.json` | Which feature modules exist, their ids, and what they require                      |

`app_configs/` and `additives/` are **gitignored by the generated `.gitignore`**. `git status` will
not show your edits there — verify by reading files, not by diffing.

To confirm the running framework version:

```bash
python -c "from webfluid import version; print(version())"
```

## The rules that keep generated code correct

1. **Nothing is on by default.** Batteries need `EXT_*` in the app config, surface features need
   `WF_*`, Additives need their id in `[additives]` **and** `WF_ADDITIVES = 1`. Code using `db`
   without `EXT_SQLALCHEMY = 1` fails at runtime, not at import.
2. **Reach batteries through the shared registry, never construct them.** `from webfluid.core.ext
   import db, babel, security, events, cache, mail, jwt, scheduler` — process-wide singletons,
   created lazily on first attribute access.
3. **Use the app factory.** Name it `prepare_fluid()` in `main.py`. `wf migrate` looks for exactly
   that name, and a module-level `Fluid(__name__)` is constructed by every tool that imports your
   modules — including ones with no app config in the environment, where the constructor raises on
   the missing `SECRET_KEY`.
4. **Run through `wf run <app>`.** Startup and shutdown hooks live in `fluid.mix()`, not in the ASGI
   lifespan protocol. An external ASGI server skips table creation, the scheduler, Additive
   registration, the static mounts and the frozen loader stack.
5. **No module-level app reference in handlers.** Use `FluidContext.current().fluid`; inside an
   Additive use `from .. import additive` **inside** the handler function (a top-level import of the
   package is circular).
6. **`fluid.config` always contains every framework key.** Index it (`fluid.config["X"]`). Use
   `.get("X", default)` only for keys *you* invented — restating a framework default creates a
   second source of truth.
7. **Secrets belong in the `.ini`; everything else belongs in `fluid/config.py`.** The `.ini` is
   gitignored and flattened into the process environment, so it is the only place a credential may
   go — and that covers values that merely *can* carry one, connection URIs above all
   (`DATABASE_URI`, `REDIS_URI`). `fluid/config.py` is committed: it is where a reader of the
   repository sees what the app actually is, and it is the only place a dict, a list or a real
   boolean can live, because the `.ini` is a flat string map. `fluid/_my_config.py` is gitignored
   and takes a maintainer's private-but-not-secret overrides. Putting a secret in `config.py`
   commits it forever; putting `APP_FRONTEND` in the `.ini` cannot work at all.
8. **Every hook has an arity contract, checked at registration time.** Startup, shutdown,
   `before_request` and `context_processor` take **0** required arguments; `after_request` takes
   **1**; event and query handlers take **1**. A mismatch raises `TypeError` where you registered
   it.
9. **Register during app assembly, never from a request.** Hooks, template loaders, page sources and
   static prefixes are frozen in the `_prepare` startup hook. Afterwards they raise `RuntimeError`.
10. **Async first.** Every I/O API has an `a*` twin — `asend`, `agettext`, `aget`, `aencode`,
    `adecode`, `async_executor`, `ahash`/`averify`. Inside `async def`, use it.
11. **Autoescape is on** for `.html`, `.htm`, `.xml`, `.xhtml`, `.svg` and every `render_string`
    source. To emit HTML on purpose, wrap it in `markupsafe.Markup` or use `| safe`; never reach for
    either on a value that came from a request.
12. **Write no comments or docstrings** when editing an existing WebFluid codebase, unless the
    project already has them. The generated style is deliberately bare.
13. **Pin the version.** Everything in a package's `__all__` follows semver; everything else is
    internal and may move between releases. Do not import from undocumented module paths such as
    `webfluid.core.fluid.main`.

## The shapes to generate

The scaffolder produces this layout and every doc page assumes it. Match it.

```text
myapp/
├── main.py              # prepare_fluid(), includes the routers
├── app_configs/app.ini  # secrets, EXT_*/WF_* switches, [additives] — gitignored
├── additives/           # feature modules
└── fluid/
    ├── config.py        # @register_config Config(MyConfig)
    ├── api/             # JSON routers, mounted under /api
    ├── app/             # HTML routes, default_response_class=HTMLResponse
    ├── models/          # db.Model subclasses — Alembic imports fluid.models by name
    ├── schemas/         # pydantic
    ├── services/        # business logic, reusable from jobs and events
    ├── events/          # signals, events, queries — registered from a hook
    ├── static/          # served at /static
    └── templates/       # searched before the framework's own
```

**Handlers live in their own module; routers are assembled in the package `__init__.py`.** This is
the only shape that works cleanly with a factory (no module-level app to close over).

```python
# fluid/app/index.py
from webfluid.core.context import FluidContext


async def handle_request():
    ctx = FluidContext.current()
    return await ctx.fluid.render("index.html")
```

```python
# fluid/app/__init__.py
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

app_router = APIRouter(default_response_class=HTMLResponse)

from fluid.app.index import handle_request as index
app_router.get("/")(index)
```

```python
# main.py
from webfluid import Fluid


def prepare_fluid() -> Fluid:
    app = Fluid(__name__)

    from fluid.app import app_router
    from fluid.api import api_router
    app.include_router(app_router)
    app.include_router(api_router)

    from fluid.events.models import register as register_events
    app.startup_hook(register_events)

    return app


if __name__ == "__main__":
    prepare_fluid().mix()
```

Database access always goes through an executor context manager, which owns the transaction:

```python
from webfluid.core.ext import db
from sqlalchemy import select
from fluid.models import MyModel


async def get(model_id: int) -> MyModel | None:
    async with db.async_executor(model=MyModel) as e:
        result = await e.exec(select(MyModel).where(MyModel.id == model_id))
        return result.first()
```

Pass `model=` on every executor call — it is how the right bind is chosen. `scalars=True` is the
default and is wrong for `select(func.count(...))`; pass `scalars=False` there.

## Task → route

| Task                         | Do this                                                                                    | Depth                         |
|------------------------------|--------------------------------------------------------------------------------------------|-------------------------------|
| Scaffold a project           | `wf create project <name>` (add `--skip-frontend` when there is no TTY)                    | `references/project-setup.md` |
| Add an app config            | `wf create app <name>` is interactive — without a TTY, write the `.ini` by hand            | `references/project-setup.md` |
| Add a setting                | Secret, or could hold one → `.ini`. Everything else → `fluid/config.py`                     | `references/project-setup.md` |
| Add a page or route          | Handler module + router `__init__.py`; template extends `fluid_base.html`                  | `references/frontend.md`      |
| Add a model                  | `fluid/models/`, then `wf migrate revision <app> -a -m "..."` → `wf migrate upgrade <app>` | `references/batteries.md`     |
| Add auth / protect a route   | `security.user_service` guards as `Depends` defaults                                       | `references/batteries.md`     |
| Translate                    | Symbolic `SCREAMING_SNAKE` keys, JSON runtime store, `update_translations` before `mix()`  | `references/batteries.md`     |
| Run code at startup          | `@app.startup_hook` in the factory (0 args)                                                | `references/runtime.md`       |
| Reach the request anywhere   | `FluidContext.current()` / `try_current()`, `cached_or`                                    | `references/runtime.md`       |
| Build a feature module       | `wf create additive <id>`; routes registered in `before_enable`                            | `references/additives.md`     |
| Make two Additives talk      | Id-scoped events/queries via `additive.unique_name()` — **never an import**                | `references/additives.md`     |
| Ship a battery-style service | A `FluidExtension` distribution, not an Additive                                           | `references/additives.md`     |
| Debug wrong behaviour        | Check the known-defect list first                                                          | `references/pitfalls.md`      |

## Verify your work

- `wf run <app> -d` — debug mode: auto-reload templates, detailed 500 page, `[dev]` config section,
  Vite dev server and HMR. Never use `-d` for a deployment.
- Read `logs/<app>/<timestamp>.log` — `wf run` redirects the child's stderr there, one file per run.
- After a model change: `wf migrate revision <app> -a -m "..."`, **read the generated revision**
  (autogenerate misses renames and emits drop+add), then `wf migrate upgrade <app>`.
- Log with `from webfluid.utils.logging import factory as log`. It is silent unless `IN_EXECUTION`
  is set, which only `wf run` does — a log line from a script or a test is dropped.

## Pull deeper detail live

The published documentation is written for agents: exact signatures, exact defaults, and the known
defects of each release. Every page exists as Markdown at the same path with a `.md` suffix.

```bash
curl -s https://docs.webfluid.dev/llms.txt
```

That index lists every page with a one-line description of what it settles. Then fetch what you
need:

```bash
curl -s https://docs.webfluid.dev/latest/ext/security.md
```

| URL                           | Contents                                                                          |
|-------------------------------|-----------------------------------------------------------------------------------|
| `/llms.txt`                   | The page index — start here                                                       |
| `/llms-full.txt`              | The entire corpus in one document (~430 KB — only when you truly need everything) |
| `/latest/.md`                 | The overview: rules that apply everywhere, release state, full known-issues list  |
| `/latest/<section>/<page>.md` | One page, e.g. `/latest/ext/sqlalchemy.md`, `/latest/additives/contract.md`       |
| `/v/<version>/<page>.md`      | A pinned version, e.g. `/v/1.0.0b2/ref/core.md`                                   |
| `/sitemap`                    | Every documentation URL, all versions                                             |

`Accept: text/markdown` on any documentation URL returns the Markdown variant without the suffix.
The Markdown mirror starts at `1.0.0b2`; older versions are HTML only. When the installed version is
newer than the published `latest`, prefer the installed package's `CHANGELOG.md` for the delta.

Reach for the live docs when you need a complete config key table, the full API surface of a
battery, or the exact enable sequence — the references below carry the working knowledge, the docs
carry the exhaustive detail.

## References

Each reference opens with a line-range index of its own sections. Read those first 30 lines, then
open only the ranges the task needs — these files run to several hundred lines each and loading one
whole to answer one question is wasted context.

| File                          | Covers                                                                                                         |
|-------------------------------|----------------------------------------------------------------------------------------------------------------|
| `references/project-setup.md` | The `wf` CLI, project layout, app configs vs. config classes, deployment                                       |
| `references/runtime.md`       | `mix()`, hooks, `FluidContext`, request flow, logging, rate limits, proxies                                    |
| `references/batteries.md`     | The eight `EXT_*` batteries — SQLAlchemy, Security, Babel, Events, Cache, Mail, JWT, Scheduling — plus Migrate |
| `references/additives.md`     | Additives, base Additives, contracts, packaging, and writing a `FluidExtension`                                |
| `references/frontend.md`      | `WF_*` switches, template resolution, `fluid_base.html`, themes, htmx and Vite                                 |
| `references/pitfalls.md`      | Known defects of the current release and the traps that produce silently wrong code                            |
