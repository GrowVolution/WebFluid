---
name: webfluid
description: Build and maintain applications on the WebFluid framework (the `webfluid` package, `Fluid`, the `wf` CLI, Additives, `webfluid.core.ext` batteries). Use whenever a project contains a fluid/ package exposing prepare_fluid(), a main.py next to it, an app_configs/ directory, an additives/ tree or a manifest.json — or when the task mentions WebFluid, Fluid, Additives, Ocean, or the wf command. Use it even when the task looks like ordinary FastAPI, SQLAlchemy or Jinja work: inside a WebFluid project those libraries are wired by the framework, and the plain-library answer is usually the wrong one.
---

# Working with WebFluid

<!-- index -->
This file is short enough to read whole; the ranges are for coming back to one section. Every file
it points to opens with an index of the same shape — read those first 30 lines, then only the ranges
the task needs.

- `47-68` **Orient before you write**
- `69-88` **Reuse before you build**
- `89-100` **Leave the human in charge**
- `101-159` **The rules that keep generated code correct**
- `160-257` **The shapes to generate**
- `258-277` **Task → route**
- `278-289` **Verify your work**
- `290-323` **Pull deeper detail live**
- `324-337` **References**
<!-- /index -->

WebFluid is a fullstack Python application runtime on top of FastAPI. `Fluid` is a `FastAPI`
subclass, so every FastAPI idiom still applies; on top of it the framework owns configuration,
logging, the event loop, the frontend build, the migration environment and a module registry.

Mental model: **FastAPI for the routes, Flask-shaped ergonomics for the app object, and a runtime
that owns the process.**

The point of the ecosystem is that you rarely start from zero. Accounts, sign-in, payments,
merchant onboarding, tokens and admin screens exist as **Additives** — packaged, centrally
maintained feature modules with a written contract. Your job is usually to install, configure and
connect them, and to write only what is genuinely specific to this application. Code you do not
write is code nobody has to review, test and maintain twice.

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
Read these first — one tool call each, and they settle what your code may use:

| Read                          | Tells you                                                                          |
|-------------------------------|------------------------------------------------------------------------------------|
| `app_configs/*.ini`           | Per app: the `EXT_*`, `WF_*` and `[additives]` switches — and every secret it uses |
| `fluid/config.py`             | The committed, non-secret settings: `APP_CONFIG`, `APP_FRONTEND`, binds, own keys  |
| `fluid/__init__.py`           | The `prepare_fluid()` factory: which routers, hooks and extensions are wired       |
| `additives/*/manifest.json`   | Which feature modules exist, their ids, and what they require                      |
| `additives/*/.agents/SKILL.md` | How to use that Additive; it points into its `CONTRACT.md` by line range          |

The `.gitignore` the scaffolder writes into a project excludes `app_configs/` and `additives/`.
`git status` will not show your edits there — verify by reading files, not by diffing.

To confirm the running framework version:

```bash
python -c "from webfluid import version; print(version())"
```

## Reuse before you build

Before you write a feature, check whether the ecosystem already ships it:

1. **An installed Additive.** Each one carries `.agents/SKILL.md` (when and how to use it) and
   `CONTRACT.md` (every route, event and query it offers, with payloads and error codes). Prefer its
   REST API and its id-scoped queries over re-implementing the same behaviour next to it.
2. **Ocean, the package hub.** `wf ocean search <term>` finds a package; `wf ocean install -a <id>`
   adds an Additive, `-e <id>` an extension, and `--prefer-stable` falls back to the latest
   prerelease while a package has no stable one. An installed package is maintained upstream: fixes
   and hardening arrive with the next release instead of living as a private fork in this
   repository.
3. **Only then write your own** — as an Additive of your own when the feature is self-contained,
   so that it can be reused and published the same way.

When an Additive almost fits, extend it through its documented extension points (queries it
consumes, signals it emits, collector queries) rather than editing its files. An edited Additive
stops receiving upstream fixes. If the contract lacks what you need, say so in your answer — that
gap is feedback for the maintainer, and it is how the shared solution improves.

## Leave the human in charge

Someone has to be able to take responsibility for what you produce. Work so that they can:

- Keep one concern per change, and say in your answer which behaviour changed — not only which
  files. A reviewer reads the summary first.
- Never weaken a gate, a check or a test to make something pass. If a gate refuses, find out why.
- Put decisions that belong to the operator into configuration with a safe default, and name the
  key in your answer: rates, limits, allowlists, external URLs, feature switches.
- Never invent a secret, a key or a credential, and never move one into a committed file.
- Prefer the documented surface over internals, so the next release does not silently break it.

## The rules that keep generated code correct

1. **Nothing is on by default.** Batteries need `EXT_*` in the app config, surface features need
   `WF_*`, Additives need their id in `[additives]` **and** `WF_ADDITIVES = 1`. Code using `db`
   without `EXT_SQLALCHEMY = 1` fails at runtime, not at import.
2. **Reach batteries through the shared registry, never construct them.** `from webfluid.core.ext
   import db, babel, security, events, cache, mail, jwt, scheduler` — process-wide singletons,
   created lazily on first attribute access.
3. **Use the app factory.** Name it `prepare_fluid()` in `fluid/__init__.py`, and keep `main.py` a
   two-line entrypoint that imports and calls it. `wf migrate` imports the `fluid` package and looks
   for exactly that name, and a module-level `Fluid(__name__)` is constructed by every tool that
   imports your modules — including ones with no app config in the environment, where the
   constructor raises on the missing `SECRET_KEY`.
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
   and takes a maintainer's private-but-not-secret overrides.
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
12. **Additives talk through id-scoped events and queries, never through imports.** Another
    Additive's package may not be installed, may be a different version, or may be replaced; its
    contract is stable, its modules are not.
13. **The framework's base classes are abstract.** `FluidExtension.expand_fluid`, the eight methods
    of `BaseCache` and `exec`/`insert`/`delete`/`flush` of the executor base are abstract: a
    subclass that misses one raises `TypeError` when it is instantiated, not when the method is
    called.
14. **Write no comments or docstrings** when editing an existing WebFluid codebase, unless the
    project already has them. The generated style is deliberately bare; the reasoning goes into
    your answer and the commit message.
15. **Pin the version.** Everything in a package's `__all__` follows semver; everything else is
    internal and may move between releases. Do not import from undocumented module paths such as
    `webfluid.core.fluid.main`.
16. **A package's documentation only looks down.** The Markdown of an Additive, an extension or an
    SDK — README, DOCS, CHANGELOG, CONTRACT, SKILL, references — names only what that package
    requires, never a package or app that builds on it. That holds for history too: a lower
    package's CHANGELOG describes a feature as its own, never as "moved here from" a consumer.
    Examples use neutral names (`my-app`, `shop`). Details in `references/additives.md`.

## The shapes to generate

The scaffolder produces this layout and every doc page assumes it. Match it.

```text
myapp/
├── main.py              # the entrypoint: calls prepare_fluid() under __main__
├── app_configs/app.ini  # secrets, EXT_*/WF_* switches, [additives] — gitignored
├── additives/           # feature modules, each with manifest.json, CONTRACT.md, .agents/SKILL.md
└── fluid/
    ├── __init__.py      # prepare_fluid(), includes the routers
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
# fluid/__init__.py
from webfluid import Fluid


def prepare_fluid() -> Fluid:
    _fluid = Fluid(__name__)

    from .api import api_router
    _fluid.include_router(api_router)

    from .app import app_router
    _fluid.include_router(app_router)

    from .events.models import register as register_events
    _fluid.startup_hook(register_events)

    return _fluid
```

This is the shape `wf create project` writes, down to the name of the local: match it, so that the
next agent reading a generated project and this page sees one shape.

`Fluid(__name__)` from inside the app package still resolves `project_root` to the project root, the
directory that holds `fluid/` — not to the package itself.

```python
# main.py
from fluid import prepare_fluid

if __name__ == "__main__":
    _fluid = prepare_fluid()
    _fluid.mix()
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

| Task                         | Do this                                                                                    | Depth                          |
|------------------------------|--------------------------------------------------------------------------------------------|--------------------------------|
| Scaffold a project           | `wf create project <name>` (add `--skip-frontend` when there is no TTY)                    | `references/project-setup.md`  |
| Add an app config            | `wf create app <name>` is interactive — without a TTY, write the `.ini` by hand            | `references/project-setup.md`  |
| Add a setting                | Secret, or could hold one → `.ini`. Everything else → `fluid/config.py`                    | `references/project-setup.md`  |
| Add a page or route          | Handler module + router `__init__.py`; template extends `fluid_base.html`                  | `references/frontend.md`       |
| Add a model                  | `fluid/models/`, then `wf migrate revision <app> -a -m "..."` → `wf migrate upgrade <app>` | `references/batteries.md`      |
| Add auth / protect a route   | An auth Additive first; otherwise `security.user_service` guards as `Depends` defaults     | `references/batteries.md`      |
| Translate                    | Symbolic `SCREAMING_SNAKE` keys, JSON runtime store, `update_translations` before `mix()`  | `references/batteries.md`      |
| Run code at startup          | `@app.startup_hook` in the factory (0 args)                                                | `references/runtime.md`        |
| Reach the request anywhere   | `FluidContext.current()` / `try_current()`, `cached_or`                                    | `references/runtime.md`        |
| Use an installed Additive    | Its `.agents/SKILL.md`, then the `CONTRACT.md` ranges it names                             | the Additive's own files       |
| Build a feature module       | `wf create additive <id>`; routes registered in `before_enable`                            | `references/additives.md`      |
| Make two Additives talk      | Id-scoped events/queries via `additive.unique_name()` — **never an import**                | `references/additives.md`      |
| Document an Additive         | `CONTRACT.md` + `.agents/SKILL.md`, then `wf agents index`                                 | `references/additives.md`      |
| Ship a battery-style service | A `FluidExtension` distribution, not an Additive                                           | `references/additives.md`      |
| Debug wrong behaviour        | Check the known-defect list first                                                          | `references/pitfalls.md`       |

## Verify your work

- `wf run <app> -d` — debug mode: auto-reload templates, detailed 500 page, `[dev]` config section,
  Vite dev server and HMR. Never use `-d` for a deployment.
- Read `logs/<app>/<timestamp>.log` — `wf run` redirects the child's stderr there, one file per run.
- After a model change: `wf migrate revision <app> -a -m "..."`, **read the generated revision**
  (autogenerate misses renames and emits drop+add), then `wf migrate upgrade <app>`.
- Log with `from webfluid.utils.logging import factory as log`. It is silent unless `IN_EXECUTION`
  is set, which only `wf run` does — a log line from a script or a test is dropped.
- After editing a `CONTRACT.md` or anything under `.agents/`, run `wf agents index` so the line
  ranges stay true; `wf agents index --check` fails when one is stale.

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
newer than the published `latest`, the release notes of the installed version (`CHANGELOG.md` in
the WebFluid repository) are the authority on the delta.

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
| `references/additives.md`     | Additives, base Additives, contracts, agent docs, packaging, and writing a `FluidExtension`                    |
| `references/frontend.md`      | `WF_*` switches, template resolution, `fluid_base.html`, themes, htmx and Vite                                 |
| `references/pitfalls.md`      | Known defects of the current release and the traps that produce silently wrong code                            |
