# Runtime: lifecycle, context, request flow, logging

## `mix()` — what owns the process

```text
1. log_factory.start_session()      handlers and level from LOG_LEVEL
2. startup phase                    every hook, registration order, each in safe_execute
3. serve                            uvicorn on SERVER_HOST:SERVER_PORT, own signal handlers off
4. wait                             on the shutdown flag OR the server task, whichever finishes
5. shutdown phase                   in a finally, so it runs on every path, REVERSE order
```

Because the wait covers the server task too, a server that dies on its own (a bound port) is
re-raised where you can read it and the shutdown hooks still run.

> **This sequence lives in `mix()`, not in the ASGI lifespan protocol.** `uvicorn main:fluid` or
> `gunicorn` runs no startup or shutdown hooks: no tables, no scheduler, no Additives, no frozen
> loader stack, no static mounts. Run WebFluid apps through `wf run`.

## Hooks

```python
app.startup_hook(fn)        # or @app.startup_hook
app.shutdown_hook(fn)       # or @app.shutdown_hook
```

|                     | Startup                     | Shutdown                       |
|---------------------|-----------------------------|--------------------------------|
| Required arguments  | **0**                       | **0**                          |
| Sync or async       | both                        | both                           |
| Order               | registration order          | **reverse** registration order |
| Exceptions          | logged, execution continues | logged, execution continues    |
| Registration window | before the server starts    | before the server stops        |

`Phase.add` calls `required_arg_count(fn)` and raises `TypeError` at **registration** time, so the
error points at the right line. After the phase has run it is sealed and adding raises
`RuntimeError`.

Hooks run sequentially: a slow hook holds up every hook after it and delays the first request. Keep
them focused — register things, warm one cache, create tables. Long-running work belongs behind the
scheduler or an event.

### What the framework registers itself

| Phase    | Hook                                                                                                                                 | Condition                 |
|----------|--------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
| startup  | `register_additives(fluid)`                                                                                                          | `WF_ADDITIVES`            |
| startup  | `scheduler.start`                                                                                                                    | `EXT_SCHEDULING`          |
| startup  | Babel translation flush                                                                                                              | `EXT_BABEL`               |
| startup  | JWT secret rotation                                                                                                                  | `EXT_JWT`                 |
| startup  | `fluid._prepare` — freeze static prefixes, mount static, freeze sources, add proxy-headers middleware, freeze the Jinja loader stack | always                    |
| startup  | `frontend.cover_fluid`                                                                                                               | `APP_FRONTEND` not `None` |
| startup  | Tailwind compile / Vite dev server or build                                                                                          | `WF_TAILWIND` / vite      |
| shutdown | `close_proxy_client`                                                                                                                 | always                    |

> `_prepare` is registered during `Fluid.__init__`, so it runs **before** any hook you add in the
> factory. Do not call `add_source`, `add_template_loader` or `static_prefixes.add` from a hook —
> call them directly during app assembly.

### Where startup work belongs

| Do it at                          | For                                                                                              |
|-----------------------------------|--------------------------------------------------------------------------------------------------|
| Module import (`fluid/config.py`) | Config classes                                                                                   |
| Factory body, before `return app` | Routers, sources, template loaders, extensions, `scheduler.add_job`, `babel.update_translations` |
| `startup_hook`                    | Events and queries, table creation, cache warming, anything needing the loop                     |
| `additive.before_enable`          | An Additive's routes, contracts and jobs                                                         |
| `shutdown_hook`                   | Flushing and closing                                                                             |

### Graceful shutdown

The runtime installs `SIGINT` / `SIGTERM` handlers (plus `SIGBREAK` on Windows) from a startup hook.
A signal sets the shutdown flag rather than killing the process:

```text
signal -> flag -> uvicorn should_exit -> in-flight request finishes
       -> shutdown hooks (reverse) -> "Server stopped."
```

Under `wf run` the CLI process forwards the signal to the child and gives it 10 seconds before
killing it. That grace period is the budget for the whole shutdown phase — keep hooks short.

## `FluidContext`

Every request is wrapped in a contextvar-backed context carrying the app, the request and a
per-request scratchpad. It is what lets `render`, `url_for` and locale resolution "just know" about
the current request.

```python
from webfluid.core.context import FluidContext

ctx = FluidContext.current()        # the context, or RuntimeError("No active FluidContext.")
ctx = FluidContext.try_current()    # the context, or None

ctx.fluid                           # the Fluid app
ctx.request                         # the starlette Request, or None
```

Use `current()` when a request is genuinely required; `try_current()` when you have a sensible
fallback — jobs, hooks, shared helpers.

> **A `FluidContext` is always truthy, even when it carries no data.** Test `try_current()` against
> `None`. (`len(ctx)` still reports the size of its storage. In beta 1 `__len__` made a plain request
> context falsy, which silently broke `get_locale`, `Themes.get` and `country_from_request`.)

### The scratchpad

```python
ctx["key"] = value
ctx["key"]                   # KeyError if absent
ctx.get("key", default); ctx.pop("key", default); "key" in ctx
ctx.keys() / ctx.values() / ctx.items()
```

Event and query handlers get `event` and `event_data` in that storage.

### `cached_or` — memoise per request

```python
FluidContext.cached_or(key, factory)
```

Calls `factory()` at most once per request and caches the result. With **no** context it simply
calls the factory, so the same helper works in a job:

```python
def pricing_tier():
    return FluidContext.cached_or("pricing_tier", _resolve_tier)
```

This is how the active locale and timezone are parsed once per request instead of once per
translated string. Reach for it whenever a value is expensive and stable within a request — the
current user's permissions, a tenant lookup, a feature-flag snapshot. Namespace the key.

### Other contexts

`FluidContext` is one of several contextvar-backed contexts sharing `BaseContext`:

| Context                      | Carries                     |
|------------------------------|-----------------------------|
| `FluidContext`               | app + request + storage     |
| `Executor` / `AsyncExecutor` | the active database session |
| `DomainContext`              | the active Babel domain     |
| `SelectorContext`            | forced locale/timezone      |
| `ClientContext`              | an open SMTP connection     |

All of them get `current()`, `try_current()` and `outer(depth=1)` (temporarily re-enter the
enclosing context, `None` if there is none). They are re-entrant: entering the same instance twice
stacks tokens.

## Request hooks

```python
@app.before_request
def require_session():
    ctx = FluidContext.current()
    if ctx.request.url.path.startswith("/admin"):
        if not ctx.request.session.get("user"):
            from fastapi.responses import RedirectResponse
            return RedirectResponse("/login")


@app.after_request
async def add_header(response):
    response.headers["X-Powered-By"] = "WebFluid"
    return response


@app.context_processor
def globals_():
    return {"brand": "My Portal"}
```

| Hook                | Required args      | Returns                                              | When                       |
|---------------------|--------------------|------------------------------------------------------|----------------------------|
| `before_request`    | **0**              | `None` to continue, or a `Response` to short-circuit | before routing             |
| `after_request`     | **1** (`response`) | a `Response`                                         | after the app produced one |
| `context_processor` | **0**              | a dict                                               | merged into every `render` |

Context processors merge as `result | ctx` — **explicit `render(**ctx)` values win.**

### The cost of `after_request`

```text
no after_request processors -> the response streams straight through
one or more                 -> the whole body is buffered so processors can see it
```

Two limits of that buffering:

1. A **streaming response** is detected the moment the app announces `more_body` and released
   unbuffered — it never reaches your `after_request` processors at all.
2. A buffered response carries the headers the app produced, `Content-Length` among them, so a
   processor that changes the body must return a **new** response rather than mutating the one it
   was handed.

Register an `after_request` processor only when you need one, and prefer one that only touches
headers: a single registered processor turns every response in the app into a buffered one.

Static paths are exempt — the request middleware passes anything matching `static_prefixes`
(`/static`, `/fluid/static`, `/frontend`, `/vite-dev`, plus every Additive's) straight through
without building a context.

## Reverse URLs

| Call                                     | Needs a request | Returns                                               |
|------------------------------------------|-----------------|-------------------------------------------------------|
| `url_for(name, **params)` (Jinja global) | no              | path; absolute with `external=True`                   |
| `fluid.url_path_for(name, **params)`     | no              | path                                                  |
| `POST /url-for`                          | yes             | `{"url": ...}`; unknown name → `404 UNKNOWN_ENDPOINT` |

With a request in the current context, `url_for` resolves through the request. Without one it falls
back to the application's route table, and `external=True` prefixes the configured `BASE_URL` —
which is what makes rendering a mail template from a job or a startup hook work.

`url_path_for` maintains a name → routes index that rebuilds itself whenever the route count
changes, and raises `NoMatchFound` when nothing matches.

## Themes

```python
fluid.add_theme(name, link)        # link is HTML: a <link rel="stylesheet"> tag
fluid.get_theme()                  # the active theme's markup
fluid.set_theme(request, name)     # store the choice in the session
```

Resolution: `request.session["theme"]` → `GLOBAL_THEME` → the framework theme. `add_theme` raises
for a duplicate, `set_theme` for an unknown name — a typo is an error, not a page that silently
keeps the old style. All three require `WF_THEMES` and raise `FrameworkException` without it.

The client-side `window.wf.switchTheme()` light/dark helper is independent of this registry.

## Rate limiting

```python
@app.get("/expensive")
@app.limit("5/minute")
async def expensive(request: Request):
    return {"ok": True}
```

The decorated function **must** take a `request: Request` parameter — slowapi reads the key from it.
A hit limit answers 429 with the usual headers. With `RATELIMIT_ENABLED = False`, `fluid.limit`
becomes a no-op decorator, so the same code runs unlimited without edits.

The limiter keys on `request.client` and never reads a forwarded header directly, so a client cannot
mint itself a fresh bucket by inventing one. Behind a reverse proxy that means every request keys on
the *proxy's* address until you turn `PROXY_FIX` on — set it, and the per-client keys come back.

> `RATELIMIT_DEFAULT` never applies — see `pitfalls.md`. Put the limit on every route that needs one.

## Proxies

```python
PROXY_FIX = True
PROXY_TRUSTED_HOSTS = "10.0.0.0/8"   # or "*", or a comma-separated list
```

With `PROXY_FIX` on, uvicorn's `ProxyHeadersMiddleware` is added in the `_prepare` startup hook, so
`request.client.host` and the scheme survive a reverse proxy.

Set `PROXY_TRUSTED_HOSTS` to the actual proxy, not `"*"`, unless nothing but your proxy can reach
the app: a trusted `"*"` means any client can claim any IP through `X-Forwarded-For`, which defeats
the rate limiter and every IP-based decision. This middleware is the *only* thing that lets a
forwarded header change `request.client` — nothing downstream reads one on its own.

General-purpose helpers: `get_proxy`, `get_websocket_proxy`, `add_proxy`, `close_proxy_client`. The
HTTP one drops the upstream's hop-by-hop and encoding headers and recomputes `Content-Length`, while
repeated headers such as `Set-Cookie` survive as separate lines.

## Logging

```python
from webfluid.utils.logging import factory as log

log.log("info line")            # INFO
log.debug / warning / error / critical("...")
log.exception(exc, "optional message")     # full traceback, at error level
```

Format: `[WF]\t[%Y-%m-%d %H:%M:%S %z] [LEVEL]\tmessage`, coloured by level. Every line goes twice:
coloured to stdout (through the active progress bar when one is open) and plain to stderr, which
`wf run` redirects into `logs/<app>/<timestamp>.log` — one file per run.

> **It only speaks during execution.** `log()` returns immediately unless `EXECUTION`
> (`enabled("IN_EXECUTION")`) is set, which **only `wf run` does**. A log call from a script, a
> `python -c`, a pytest run or a management command is silently dropped. Set `IN_EXECUTION=1` in the
> environment if you want output there.

Verbosity follows `LOG_LEVEL`; handlers and level are installed by `start_session()` from `mix()`.
Configuring the `webfluid` / `webfluid.additives` loggers yourself is pointless — `start_session()`
clears and replaces their handlers.

Anything running inside an Additive is attributed to `webfluid.additives` automatically: the
Additive `Router` wraps every endpoint in `factory.additive_context(fn)`.

Rules: log messages, not data dumps. Use `log.exception(e, context)` in an `except` block, never
`log.error(str(e))` — the traceback is the part that tells you where it happened. Never log secrets,
tokens, passwords or session contents. Prefer the factory over `logging.getLogger(__name__)`.

## Useful helpers

```python
from webfluid.utils import (
    enabled, safe_string, camel_to_snake, get_root_path,
    required_arg_count, async_result, safe_execute, run_in_executor,
    Version, check_required_version
)
```

| Function                                 | Notes                                                          |
|------------------------------------------|----------------------------------------------------------------|
| `enabled(key)`                           | A **dynamic** env read, unlike the `core.constants` snapshots  |
| `safe_string(text)`                      | Everything outside `[a-zA-Z0-9_-]` → `_`. The Additive id rule |
| `camel_to_snake(text)`                   | `MyModel` → `my_model`. The `__tablename__` rule               |
| `await async_result(value)`              | Await it if it is a coroutine, otherwise return it             |
| `await safe_execute(fn, reraise, *args)` | Call sync or async; `reraise=False` logs and returns `None`    |
| `await run_in_executor(fn, *args)`       | Run a blocking call off the event loop                         |

`run_in_executor` is the correct answer whenever you must call something blocking from async code —
a sync SDK, a CPU-bound hash, a sync database driver.

`webfluid.core.constants` (`DEBUG`, `EXECUTION`, `THEMES`, `TAILWIND`, `PROCESSING`, `ADDITIVES`,
`EXT_*`) are **module-level constants read once at import time**, not live values. A test that
changes `os.environ` afterwards changes nothing — use `enabled(key)` for a dynamic read.

## Exceptions

```text
FrameworkException
├── FrontendException
│   ├── NodeError
│   └── TailwindError
├── AdditiveException
│   └── ManifestError
└── OceanError            (.status, .detail)
```

Catch `FrameworkException` to handle any framework-level failure uniformly, and the specific
subclass when you can actually recover. Never wrap framework calls in a bare `except Exception` —
the exception handler already turns an unhandled one into a proper 500.
