# Project setup, configuration and the CLI

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `25-59` **The command tree**
- `60-94` **The project layout**
- `95-112` **What `Fluid(import_name)` does, in constructor order**
- `113-225` **`app_configs/<name>.ini`**
  - `164-178` `EXT_*` — batteries
  - `179-194` `WF_*` — surface features
  - `195-200` `[additives]`
  - `201-212` Secrets from files
  - `213-218` `[dev]`
  - `219-225` Environment the CLI injects
- `226-314` **Config classes**
  - `259-304` What belongs where
  - `305-314` Reading config
- `315-335` **One project, many apps**
- `336-365` **`wf run` and deployment**
- `366-394` **Ocean**
<!-- /index -->

## The command tree

```text
wf
├── create      project <name> [-sd] [-sf] [-bf] | app <name> [-sl N] | additive <id>
├── ocean       login / logout / search / install / publish
├── run         <app> [-h host] [-p port] [-l level] [-d] [-i]
├── node        forward a command to the bundled Node runtime
├── tailwind    forward a command to the Tailwind CLI
├── migrate     (extension) init / revision / upgrade / downgrade  — each takes <app>
└── babel       (extension) extract / compile
```

`migrate` and `babel` are **extension CLIs**: on every invocation `wf` walks
`entry_points(group="webfluid.extensions")` and mounts each extension's `_cli` Typer app under its
entry-point name. Your own extension gets a `wf <name> …` group the same way.

| Command                    | Working directory     | Touches                                          |
|----------------------------|-----------------------|--------------------------------------------------|
| `wf create project <name>` | anywhere              | creates `<name>/`                                |
| `wf create app <name>`     | project root          | `app_configs/<name>.ini`                         |
| `wf create additive <id>`  | project root          | `additives/<id>/`                                |
| `wf run <app>`             | project root          | needs `main.py` **and** `app_configs/<app>.ini`  |
| `wf migrate …`             | project root          | reads `app_configs/<app>.ini`, writes `migrate/` |
| `wf ocean install`         | project root          | writes `additives/`, `extensions/`               |
| `wf ocean publish`         | the package directory | reads `manifest.json` or `pyproject.toml`        |

> **The scaffolders are interactive and have no non-interactive flag.** Without a TTY, run
> `wf create project <name> --skip-frontend` (which asks nothing) and write `app_configs/<name>.ini`
> by hand. All three refuse a non-empty target — never regenerate over an existing project; write
> the missing file by hand instead.

Run npm through `wf node npm …`, never a global npm. It guarantees the runtime the framework will
use at boot and works on machines with no Node installed.

## The project layout

```text
myapp/
├── main.py                  # prepare_fluid(), includes the routers
├── package.json             # npm workspace (Vite frontends only)
├── vite.config.js           # orchestrator, written by the CLI — do not hand-write
├── app_configs/app.ini      # one .ini per app: secrets + switches — gitignored
├── additives/               # feature modules — gitignored
└── fluid/
    ├── config.py            # @register_config Config(MyConfig) — committed, non-secret
    ├── _my_config.py        # a maintainer's local overrides — gitignored
    ├── api/{__init__,health}.py, api/v1/__init__.py
    ├── app/{__init__,index}.py
    ├── frontend/            # Vite workspace (type vite only)
    ├── models/ schemas/ services/ events/ utils/
    ├── static/css/tailwind_raw.css, static/img, static/js
    └── templates/index.html
```

The split is load-bearing:

| Directory         | Why it matters                                                    |
|-------------------|-------------------------------------------------------------------|
| `fluid/api`       | Mounted under `/api`; JSON default response class                 |
| `fluid/app`       | Router created with `default_response_class=HTMLResponse`         |
| `fluid/models`    | The generated Alembic `env.py` imports `fluid.models` **by name** |
| `fluid/events`    | Registered from a startup hook, not at import                     |
| `fluid/static`    | Served at `/static`, reversed with route name `static`            |
| `fluid/templates` | Searched **before** the framework's own templates                 |

`.gitignore` written by the scaffolder excludes `app_configs/`, `additives/`, `migrate/`,
`translations/`, `logs/`, `_my_config.py`, `tailwind.css`, `*.db`. Editing an Additive in place
shows nothing in `git status` — verify by reading files.

## What `Fluid(import_name)` does, in constructor order

1. `project_root` from `import_name`; `additive_root = project_root / "additives"`.
2. `init_configs()` imports `fluid.config` and the `config` module of every **enabled** Additive.
3. `Config()` is built: `DefaultConfig`, then every `@register_config` class in priority order.
   **After this, `fluid.config` holds every key the framework knows.**
4. `SECRET_KEY` is asserted. Missing → `FrameworkException`.
5. `self.name` comes from `APP_NAME` (set by `wf run`), lowercased and sanitised.
6. `FastAPI.__init__(**config["APP_CONFIG"])`.
7. Lifecycle phases, Jinja environment, sources, themes, static mounts, limiter, server.
8. Additive registration queued as a startup hook, enabled extensions expanded, frontend set up.
9. Middleware: request, session, processing (`WF_PROCESSING`), proxy-client shutdown hook.

Consequences: config classes must be registered **before** the constructor (putting them in
`fluid/config.py` is enough); batteries are usable from step 8 onwards, i.e. anywhere in a request
or a hook, but not before `Fluid(...)` returns; `ProxyHeadersMiddleware`, static mounts and the
Jinja loader stack are finalised in the `_prepare` **startup hook**, not the constructor.

## `app_configs/<name>.ini`

**This file is the project's secret store.** It is gitignored, it is never published, and its whole
contents become the application's environment. Settings that are not secret and not per-deployment
belong in `fluid/config.py` instead — the split is spelled out under *What belongs where* below, and
getting it backwards is the most common configuration mistake made in a WebFluid project.

`wf run <name>` parses the file with `configparser` (`optionxform = str`, keys keep their case),
flattens **every section** into one environment mapping and spawns `python main.py` with it. Section
names are pure organisation — with one exception, `[dev]`.

Because of the flattening, **two sections declaring the same key silently collide.** Keep keys
unique across the file.

```ini
[general]
SECRET_KEY = supersecret

[extensions]
EXT_SCHEDULING = 0
EXT_SQLALCHEMY = 1
EXT_BABEL = 1
EXT_SECURITY = 0
EXT_EVENTS = 1
EXT_CACHE = 0
EXT_MAIL = 1
EXT_JWT = 0

[features]
WF_THEMES = 1
WF_TAILWIND = 1
WF_CHECK_FRONTEND = 0
WF_BUILD_FRONTEND = 1
WF_PROCESSING = 1
WF_ADDITIVES = 1

[data]
DATABASE_URI = sqlite:///app.db
REDIS_URI = redis://localhost:6379

[additives]
portal = 1

[dev]
DATABASE_URI = sqlite:///dev.db
```

Both switch families are read from the environment at **import time** of `webfluid.core.constants`
through `enabled(key)`: true for `"true"`, `"1"` or `"yes"` (case-insensitive), false for everything
else including an absent key.

### `EXT_*` — batteries

| Switch           | Enables                                   | Hard requirements                                 |
|------------------|-------------------------------------------|---------------------------------------------------|
| `EXT_SCHEDULING` | APScheduler `AsyncIOScheduler`            | —                                                 |
| `EXT_SQLALCHEMY` | `db` — engines, sessions, `Model`         | —                                                 |
| `EXT_BABEL`      | `babel` — gettext, formatters, `/ws/i18n` | **`EXT_SQLALCHEMY`**                              |
| `EXT_SECURITY`   | `security` — users, gates, CSRF, OAuth    | `EXT_SQLALCHEMY`; `SECURITY_SECRET` in production |
| `EXT_EVENTS`     | `events` — signals, queries, `/ws/events` | —                                                 |
| `EXT_CACHE`      | `cache` — redis or legacy backend         | —                                                 |
| `EXT_MAIL`       | `mail` — sync and async SMTP              | —                                                 |
| `EXT_JWT`        | `jwt` — encode/decode + key rotation      | **`EXT_SCHEDULING` and `EXT_CACHE`**              |

A missing hard requirement raises `FrameworkException` during `Fluid(...)`, not at first use.

### `WF_*` — surface features

| Switch              | Effect                                                                                                                                                                     |
|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `WF_PROCESSING`     | The shared template context (`url_for`, `theme`, `src`, `LANG`, `YEAR`, `id`, gettext fallback), the request logger, the styled error pages, `/wf-identity` and `/url-for` |
| `WF_TAILWIND`       | Compiles every `tailwind_raw.css` into a minified `tailwind.css` on startup; publishes the `wf_tailwind` Jinja global                                                      |
| `WF_THEMES`         | `add_theme` / `get_theme` / `set_theme`; also selects the raw stylesheet name (`tailwind_raw.css` on, `tailwind_no_themes.css` off)                                        |
| `WF_CHECK_FRONTEND` | Production only: `npm run check --workspaces`; a type error aborts the boot                                                                                                |
| `WF_BUILD_FRONTEND` | Production only: `npm run build --workspaces`; a failed build aborts the boot                                                                                              |
| `WF_ADDITIVES`      | Registers and enables every Additive switched on in `[additives]`                                                                                                          |

`WF_CHECK_FRONTEND` and `WF_BUILD_FRONTEND` are **not read in debug mode**.

**Turn `WF_PROCESSING` on for anything that renders HTML.** Without it there is no `url_for`, no
`theme`, no `src` and no `_()` fallback, so `fluid_base.html` renders a broken document.

### `[additives]`

One line per Additive **id** (the manifest's `id` wins over the directory name). `WF_ADDITIVES` must
also be on. Base Additives are never listed — they are pulled in by whichever default Additive
extends them.

### Secrets from files

Any key may carry a `_FILE` suffix and point at a path. The CLI reads the file (UTF-8) and exposes
the contents under the key **without** the suffix; a missing file leaves the path string as a
fallback. `wf run` and the `wf migrate` environment share the parser, so a migration also sees the
real secret. This is the correct way to feed Docker and Kubernetes secrets in.

```ini
[general]
SECRET_KEY_FILE = /run/secrets/secret_key
```

### `[dev]`

The one section name with meaning: applied **only** under `-d`. The CLI iterates sections in file
order, so keep `[dev]` **last**. `wf migrate` reads every section unconditionally and does **not**
apply `[dev]` — use a separate app config for a development database.

### Environment the CLI injects

`APP_NAME`, `SERVER_HOST`, `SERVER_PORT`, `IN_EXECUTION=1`, `DEBUG_MODE` (under `-d`), `LOG_LEVEL`,
`COLUMNS`/`LINES`, `PYTHONIOENCODING`, `PYTHONUNBUFFERED`, `ENABLED_ADDITIVES`. Do not set these in
the `.ini`. Two more are read but never set: `DEV_AUTO_INSTALL=1` (debug only — calls
`Additive.install()` on every registration) and `OCEAN_API` / `OCEAN_AUTH`.

## Config classes

```python
# fluid/config.py
from webfluid.core.config import register_config

try: from fluid._my_config import MyConfig
except ImportError:
    class MyConfig: pass


@register_config(10)
class Config(MyConfig):
    APP_CONFIG = {"title": "myapp", "version": "1.0.0"}
    APP_FRONTEND = {"type": "htmx", "alpine": True}
```

The merge collects every **upper-case** attribute across the whole MRO in reverse, so:

1. Only `UPPER_CASE` names are config — `my_setting = 1` is invisible.
2. Inheritance works; the subclass wins. That is what the `MyConfig` pattern rests on.
3. `register_config(priority)` takes 1–10 (default 1); higher wins, same-priority classes apply in
   registration order.

The `MyConfig` pattern is the framework's convention for public repositories: the settings everyone
shares in `config.py` (committed), a maintainer's own overrides in `fluid/_my_config.py`
(gitignored). A clone without the file still starts. Adopt it in every project — but note that
`_my_config.py` is for values that are *private*, not *secret*; secrets go in the `.ini`, as the
next section spells out.

**An Additive ships its own defaults the same way**, from `additives/<id>/config.py`, at priority 1
so the host app's priority-10 class can override them.

### What belongs where

Two places hold settings and they are not interchangeable. The `.ini` is **gitignored and loaded
into the process environment**; `fluid/config.py` is **committed and read by everyone who clones the
repository**. That difference is the entire rule.

**`app_configs/<app>.ini` — secret, or potentially secret.**

| Put here                     | Examples                                                                         |
|------------------------------|-----------------------------------------------------------------------------------|
| Credentials                  | `SECRET_KEY`, `SECURITY_SECRET`, `MAIL_PASSWORD`, OAuth client secrets, API keys  |
| Anything that *can* hold one | `DATABASE_URI`, `REDIS_URI`, `RATELIMIT_STORAGE_URI`, any other connection URI    |
| Per-deployment values        | Hosts, ports, bucket names, the `[dev]` overrides                                 |
| What this app *is*           | `EXT_*`, `WF_*`, `[additives]`                                                    |

"Potentially secret" is the part that gets missed. `DATABASE_URI = sqlite:///app.db` carries no
credential today, but the same key in production is `postgresql://app:hunter2@db.internal/app` — a
URI is a credential-shaped value, so it belongs in the `.ini` from the first commit rather than
being moved on the day it starts to matter. The same reasoning covers any host only reachable from
inside your network: a name worth keeping out of a public repository is worth putting in the `.ini`.

**`fluid/config.py` — non-secret, and everything the repository should show.**

| Put here                       | Examples                                                                                       |
|--------------------------------|-------------------------------------------------------------------------------------------------|
| Application shape              | `APP_CONFIG`, `APP_FRONTEND`, `BASE_URL`, `GLOBAL_THEME`                                        |
| Policy every deployment shares | Cookie flags, `RATELIMIT_DEFAULT`, `SECURITY_PASSWORD_REQUIREMENTS`, `BABEL_SUPPORTED_LOCALES`  |
| Your own keys                  | `MYAPP_*`, `<ADDITIVE_ID>_*`                                                                    |
| Every structured value         | `SQLALCHEMY_BINDS`, `SQLALCHEMY_ENGINE_OPTIONS`, `JWT_AUDIENCES`, any dict, list or tuple       |

The last row is not a preference. The `.ini` is a flat string→string map, so a dict, a list, a tuple
or a real boolean has nowhere else to go — `APP_FRONTEND = {"type": "vite"}` in an `.ini` reaches
the application as a string and fails somewhere far from where you wrote it.

**`fluid/_my_config.py` — private, but not secret.** Gitignored, imported by `config.py` behind a
`try`, and the right home for a maintainer's own `BASE_URL`, a personal SMTP host or an experiment
they are not ready to commit. It is a normal Python module inside the package: it is copied into a
wheel or a container image like any other file, so it keeps things out of the *repository*, not out
of the *artefact*. Real secrets still go in the `.ini`.

When a value could plausibly go either way, put it in the `.ini`. A non-secret there costs one
duplicated line per app config; a secret in `config.py` is in the git history for good.

For a secret that should not sit in a readable file at all, use the `*_FILE` indirection described
above — the key names a path, and the CLI substitutes the file's contents.

### Reading config

```python
fluid.config["SESSION_COOKIE_SECURE"]      # framework key: always present
fluid.config.get("MYAPP_UPSTREAM", "...")  # your own key: may be absent
```

Prefix your own keys (`MYAPP_*`, `<ADDITIVE_ID>_*`) so they cannot collide. The complete default
table lives at `/latest/config/config-class.md`.

## One project, many apps

`fluid.name` comes from the config name, so one `main.py` can assemble different applications:

```python
def prepare_fluid() -> Fluid:
    app = Fluid(__name__)

    if app.name == "api":
        from fluid.api import api_router
        app.include_router(api_router)
    elif app.name == "web":
        from fluid.app import app_router
        app.include_router(app_router)

    return app
```

`wf run api` and `wf run web` then serve different route sets, switches, databases and Additives
from one repository. Each app also gets its own migration history under `migrate/`.

## `wf run` and deployment

| Flag                   | Default     | Effect                                                   |
|------------------------|-------------|----------------------------------------------------------|
| `-h` / `--host`        | `127.0.0.1` | → `SERVER_HOST`                                          |
| `-p` / `--port`        | `8000`      | → `SERVER_PORT`                                          |
| `-l` / `--loglevel`    | `info`      | → `LOG_LEVEL` (ignored under `-d`, which forces `debug`) |
| `-d` / `--debug`       | off         | Debug mode                                               |
| `-i` / `--interactive` | off         | Control menu (restart, stop, join log, clear logs)       |

Debug mode: `SESSION_COOKIE_SECURE` off, `STATIC_MAX_AGE` 0 plus a `?t=` cache-buster, Jinja
`auto_reload` on, the detailed `errors/debug/500.html` with traceback in JSON bodies, the Vite dev
server proxied for HMR, the `[dev]` section applied, `LOG_LEVEL` forced to `debug`. `-d` with
`-p 5173` is refused — that port belongs to Vite. **Never deploy with `-d`.**

A workable container shape:

```dockerfile
RUN wf node npm install && wf node npm run build --workspaces
ENV WF_CHECK_FRONTEND=0 WF_BUILD_FRONTEND=0
CMD ["wf", "run", "prod", "-h", "0.0.0.0", "-p", "8000"]
```

Bind to `0.0.0.0` inside a container. Put secrets behind `*_FILE` keys pointing at mounted files.

**One process per app.** `wf run` has no worker model, and the event bus, the legacy cache and the
scheduler are all in-process. Scale by running several containers behind a proxy — and remember that
means separate event buses, separate legacy caches, and the scheduler firing once per process. Use
Redis for the cache, and give the scheduler its own single-instance app config.

## Ocean

```bash
wf ocean search auth --additives --oss-only
wf ocean install -a portal -e stripe      # -a → additives/<id>, -e → extensions/<id> + pip -e
wf ocean install -a portal==1.2.0         # pinned; --alpha/--beta/--rc switch the channel
wf ocean install -b 000123 -a portal      # a bundle expands to the packages it contains
wf ocean install -a portal -p             # --pre: the latest prerelease, whatever its channel
wf ocean install -a portal -ps            # --prefer-stable: stable, else the latest prerelease
wf ocean publish                          # from the package directory
```

The bundle id is the first column of `wf ocean search`'s bundle table; leading zeros are optional.
`-b` is exactly equivalent to naming every package the bundle contains, so bundles and single
packages mix freely — a package requested twice is installed once, with a duplication warning, and
an explicit `id==version` beats the bundle's unpinned entry.

Anything already present is **skipped rather than overwritten**, so re-running is safe. Each
installed Additive then runs its `install()` routine: resolve and pull required Additives
recursively, copy its `extract/` files into the host app (never overwriting), pip-install its
manifest `packages`.

**Installing does not enable.** Add the id to `[additives]` in every app config that should load it,
ensure `WF_ADDITIVES = 1`, and re-run the migration cycle if it brings models.

The archive is the working directory minus `.git`, `__pycache__`, `node_modules`, editor folders,
compiled files **and** everything `.gitignore` excludes (nested files included, negations honoured).
Check that file before publishing: a gitignored secret is not shipped, an untracked build artefact
is.
