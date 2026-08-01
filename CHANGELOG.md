# Changelog

All notable changes to WebFluid are documented here. The project follows
semantic versioning for everything listed in a package's `__all__`; anything
else is internal and may change in any release.

## 1.0.0b1

First beta. This release completes the SOLID refactor started after `1.0.0a2`,
fixes six regressions introduced by it, and removes the largest performance
bottlenecks in the request path.

### Breaking changes

| Removed / renamed                                  | Replacement                                                                   |
|----------------------------------------------------|-------------------------------------------------------------------------------|
| `Fluid.app_root`                                   | `Fluid.project_root` (the old name still works and warns)                     |
| `Fluid.app_static`, `Fluid.framework_static`       | `Fluid.static_files`                                                          |
| `Fluid.asgi_app`                                   | gone — `PROXY_FIX` now adds a normal middleware                               |
| `Fluid.state.limiter`                              | `Fluid.limit`                                                                 |
| `Fluid.static_prefixes` (a `set`)                  | `StaticPrefixes` object with `add()` / `matches()`                            |
| `HookPhase.add_hook`, `RequestPhase.add_processor` | `Phase.add`                                                                   |
| `Lifecycle.run_hooks()`                            | `Lifecycle.run_startup()` / `run_shutdown()` / `run_before()` / `run_after()` |
| `FluidContext.get_ctx_data`                        | `FluidContext.cached_or`, or the extension's own config                       |
| `utils.core.final_version`                         | `packaging.version.Version`                                                   |
| `FluidVersion(major, minor, patch)`                | `FluidVersion(*parts)`, now a `packaging` version                             |
| `core.config.ConfigMeta`                           | gone — configs are merged as plain dictionaries                               |
| `build_config()` returning a class                 | returns a `dict`                                                              |
| `core.processing.error.add_exception_handler`      | `install_error_handler`                                                       |
| `core.fluid.middleware.http`                       | `core.fluid.middleware.request`                                               |
| `Fluid.render(template, is_string=True, ...)`      | `Fluid.render_string(source, ...)`                                            |
| `core.constants.WF_STATIC`                         | `core.constants.FRAMEWORK_STATIC`                                             |
| `core.constants.WF_OCEAN`, `OCEAN_AUTH`            | `core.constants.HUB_API` / `HUB_AUTH`                                         |
| `core.constants.FRAMEWORK_ROOT`                    | `core.identity.FRAMEWORK_ROOT`                                                |
| `check_required_version(..., "wf")`                | `check_required_version(..., "framework")` (the new default)                  |
| `AUTH_API` environment variable                    | `OCEAN_AUTH`, derived from the hub name                                       |

`is_string` is gone entirely: `Fluid.render()` and `Additive.render()` no longer
inspect it, so passing it now reaches the template as an ordinary variable and
the source string is looked up as a template name.

`Additive.version` is now an attribute instead of a property.

Model relationships in the security and babel extensions were audited one by one
against how the framework actually reads them, instead of carrying the blanket
`lazy="selectin"` the alpha applied to all of them. Only the two that are read
by attribute stay eager — `User.totp_secret` and `User.webauthn_credentials`,
which `two_fa.requirement_fulfilled` reads on every gated request. Those two
have no choice: `current_user` expunges the user and closes its session, so a
relationship that is not loaded up front cannot be loaded at all.

Everything else is now `lazy="raise_on_sql"`:

- `User.roles`, `Role.permissions` — the admin, role and permission gates query
  the association tables directly and never navigate the relationship.
- `User.identities`, `User.backup_codes` — read nowhere in the framework, and
  both hold credential material that has no place in a template.
- `Role.users`, `Permission.roles`, `Identity.user`, `TOTPSecret.user`,
  `WebAuthnCredential.user`, `BackupCode.user` — reverse sides; `Role.users` was
  the unbounded fan-out in the `is_admin` gate.
- `I18nMessage.key`, `I18nKey.messages` — the per-key lookups use
  `I18nMessage.key` only as a SQL expression (`.has(...)`); the one place that
  reads it as an attribute, the bulk catalog load, joins and eager-loads it
  explicitly with `contains_eager()`.

Code that navigates any of those must now load it explicitly — `selectinload()`
on the query, or a separate query. Reading `user.roles` in a handler or template
is the most likely thing to break. The cascades are unchanged: deleting a `User`
still deletes its identities, codes and credentials.

### Fixed

- `Additive.before_request` and `Additive.after_request` raised `AttributeError`.
  The three lifecycle implementations diverged during the refactor; they now
  share one `Phase` type.
- The `/ws/events` endpoint closed immediately under uvicorn because the socket
  handler was spawned as a task and the endpoint returned.
- `check_required_version` compared only the numeric release parts, so
  `>1.0.0a1` did not match `1.0.0a2`, `==1.0.0a1` matched `1.0.0b1`, and
  `>=1.0.0b1` matched `1.0.0a1`. Version handling now uses `packaging`.
- `Manifest.check_requirements` emptied the manifest's own requirement
  dictionary, so a second check reported success.
- `try_import` re-raised when a parent package was missing, which broke
  projects generated with `--skip-defaults`.
- `installed_additives` re-scanned the additive directory on every call when a
  project had no additives.
- `Frontend.include` raised `AttributeError` when Tailwind was enabled on an
  uncovered frontend; `cover_additive` corrupted its own prefix when called
  twice.
- `Themes.set` refused to set a theme that actually existed.
- `Babel.domain_context` wrapped every decorated callable in an `async` wrapper,
  so a synchronous function decorated with it returned a coroutine instead of
  its value. A `@property` over it — the way a model exposes a translated
  column — yielded a coroutine on attribute access, which surfaced as
  `'coroutine' object is not iterable` once the value reached a response
  encoder and as `cannot reuse already awaited coroutine` once a template
  resolved the same attribute twice. It branches on the wrapped function again,
  as it did in `1.0.0a2`.
- `TransactionService.load` reads `I18nMessage.key` as an attribute to decide
  whether a key belongs in the cache, which `lazy="raise_on_sql"` turns into
  `InvalidRequestError: 'I18nMessage.key' is not available`. Every application
  with `EXT_BABEL` died in its startup hook. The bulk load joins `I18nKey` and
  loads it with `contains_eager()`, which also replaces the `EXISTS` subquery
  the domain filter used with a plain join.
- `wf run` streamed the application's console output through a text-mode pipe,
  so Python's universal-newline translation turned every carriage return into a
  newline before the parent ever saw it. A `tqdm` bar that redraws itself in
  place arrived as one line per frame, interleaved with the blank lines and the
  rows of spaces it writes to clear itself, and `readline()` held each frame
  back until the next newline arrived. The pipe is read as bytes now and
  forwarded in whatever chunks arrive, decoded incrementally so a multi-byte
  character split across two reads survives. The reader stops at EOF instead of
  spinning on empty reads once the application exits.
- `wf run` gave the application process no terminal geometry, so `tqdm` fell
  back to its 10-character bar and to ASCII blocks. `COLUMNS`, `LINES` and
  `PYTHONIOENCODING` are exported to the child and `progress_bar` passes an
  explicit `ncols`. The encoding follows the parent's console, so a redirected
  `wf run` degrades to ASCII bars in the file instead of failing to encode the
  Unicode ones.
- `LogService.clear_logs` deleted the log file it was writing to whenever the
  application was not running, which raises `PermissionError` on Windows and
  detaches the open handle everywhere else. It keeps the current run's file and
  drops the rest; it no longer takes a lifecycle.
- `LogService.streaming` now decides whether output is echoed, not whether the
  reader lives. The reader runs from the first `start_stream` or `join_log` to
  EOF, so nothing is lost between `Stopping application...` and the last
  shutdown hook, and the application can never block on a full pipe while its
  output is muted in the interactive menu. `__exit__` joins the reader, which
  puts the shutdown phase — its log lines and its progress bar — ahead of the
  closing message instead of racing it. Repeatedly joining the log reuses the
  running reader instead of starting a second one on the same pipe.

### Performance

Measured on Windows 11 / Python 3.14 with `benchmarks/bench.py`.

- **Template rendering is ~3.8x faster** (491 µs → 128 µs for a page with 22
  template resolutions). Jinja ran with `auto_reload=True`, stat-ing every
  template on every render; it now follows `DEBUG`.
- **The request pipeline no longer uses `BaseHTTPMiddleware`** (+28 % latency
  per request from its anyio task group and memory streams). A pure ASGI
  middleware replaces it; streaming responses pass through unbuffered.
- **The `is_admin` gate went from 7 queries to 1**, and no longer hydrates every
  user holding the matching role — an unbounded result set on every request
  behind `require_admin`.
- **`current_user` went from 7 queries to 3.** Loading the current user eagerly
  pulled its identities, roles, role permissions, backup codes, TOTP secret and
  WebAuthn credentials on every authenticated request; only the last two are
  ever read. It also **releases its database connection** instead of holding it
  for the whole request, which capped concurrency at the pool size.
- **`import webfluid.cli` dropped from 845 ms to ~245 ms** and
  `from webfluid import Fluid` from 1497 ms to ~600 ms. `webfluid.core.ext`
  instantiated all eight extensions at import time regardless of the `EXT_*`
  flags; extension singletons, `utils.core.proxy`, GitPython, slowapi and
  uvicorn's proxy headers are now imported on first use.
- `HashService` gained `ahash` / `averify`, which run Argon2 (~40 ms of pure
  event-loop blocking per login) on a dedicated thread pool.
- `JWTManager.adecode` no longer makes a synchronous Redis call inside the async
  path and needs one round trip instead of three for a token carrying a `kid`.
- `url_for` resolves through a name index instead of scanning every route.
- The rendered `src()` block is joined once at startup instead of on every
  render, and in debug mode it is no longer built twice.
- `get_locale` / `get_timezone` cache their result per request instead of
  re-parsing `Accept-Language` for every translated string. An active locale or
  timezone selector still wins.
- `LegacyCache` uses an expiry heap instead of registering one APScheduler job
  per cached key, and no longer requires `EXT_SCHEDULING`.
- Static files are served with `Cache-Control: public, max-age=31536000`
  (configurable via `STATIC_MAX_AGE`, `0` in debug).
- Database engines are created on first use, so a bind that is only ever used
  synchronously no longer opens an async pool as well.

### Changed

- `DefaultConfig` is now the single source of truth for every default. Consumers
  read `fluid.config["KEY"]` instead of repeating the default inline — the
  duplicated `RATELIMIT_STORAGE_URI` default had already drifted.
- Extensions expose their services through a `Delegated` descriptor instead of
  repeating an `_ensure_initialized()` guard on every forwarding property.
- `Additive` delegates router layout, template loader and enable rules to a
  `BaseKind` / `FeatureKind` strategy instead of branching on `is_base` in four
  places.
- `Router.add_api_route` forwards `**kwargs` instead of restating FastAPI's 25
  parameters, and builds its middleware chain once instead of per request.
- `Manifest` no longer resolves dependencies; `RequirementChecker` does.
- `Sources`, `StaticPrefixes` and `Loaders` share a `Freezable` base.
- `BaseContext.try_current()` returns `None` instead of raising, removing the
  exception-driven control flow from the request path.
- Both session factories run with `expire_on_commit=False`. Only the async one
  did, so a row read through `db.executor(...)` expired on the way out of the
  block and raised `DetachedInstanceError` on the next attribute access, while
  the identical read through `db.async_executor(...)` stayed usable. Rows
  survive their executor now, whichever one produced them.
- `Fluid.__init__` is split into named build phases so the construction order is
  explicit.
- The default stylesheets (`tailwind_raw.css` and `tailwind_no_themes.css`) no
  longer bottom out in a hardcoded `#060f1f` navy. Page and error backgrounds,
  the nav, footer, dropdowns, cards and traceback frames now derive from four
  surface tokens declared on `:root`: `--wf-blend` (the theme's structural hue —
  `--primary-5` tinted with `--secondary-5`), `--wf-deep`, `--wf-veil` and
  `--wf-sunk`, plus `--wf-page` for the full page gradient, which adds a third
  glow from `--tertiary-4` along the bottom edge. A theme that is not blue-grey
  no longer ends in a blue-grey lower half, and embedded third-party surfaces
  branded from the same theme sit on a background that matches them. Every token
  falls back to the `--default-*` ramp, so a theme that only defines the neutral
  scale still renders. Themes keep working unchanged; only the derived tones
  move.

### Added

- An async Babel API: `Babel.agettext`, `angettext`, `apgettext` and
  `anpgettext`, backed by `MergedTranslations.agettext` and friends and by
  `TransactionService.aget` / `_afetch`, which read uncached keys through an
  async session instead of blocking the loop. Nothing synchronous changed, and
  the Jinja i18n callables deliberately keep using the synchronous methods —
  the new ones are for extension and application code that can await. There is
  no `alazy_gettext`: `LazyString` resolves through `str()`, which cannot await.
- `tests/` — 136 tests covering the lifecycle contracts, request pipeline,
  version resolution, additive enabling, the events WebSocket (against a real
  uvicorn server, since `TestClient` does not reproduce the failure), the
  security gates' query counts and relationship loading strategies, the sync and
  async translation lookups, and the cache backends. Two of them mirror an
  actual run rather than a unit: `test_bootstrap.py` mixes an application with
  `EXT_SQLALCHEMY` and `EXT_BABEL` enabled and runs its startup and shutdown
  phases against a real database, which is where the catalog load regressed,
  and `test_console.py` drives `wf run`'s process lifecycle and log stream
  against a real child process, asserting on the exact bytes that reach the
  console. `test_sqlalchemy.py` pins what the two executors guarantee: rows
  outlive their block, a raised exception rolls the transaction back, and
  `ensured_executor` joins an open one instead of nesting a second session.
- `benchmarks/bench.py` — import time, render time and request time with
  budgets, so the regressions above cannot come back silently.
- `scripts/check_stubs.py` — verifies that the stub tree mirrors the runtime
  tree and that every `__all__` entry is stubbed.
- `core/identity.py` — the single module a fork edits to make the framework its
  own. It holds the framework id, display name, abbreviation, site and docs
  URLs, and the hub name and endpoints; everything else that used to hardcode
  one of those is now derived from it. The environment prefix (`WF_THEMES` and
  friends), the logger names, the extension entry-point group, the additive
  manifest's version key, the identity route, the hub token file, the base
  template name, the static mount and the `wf_static` / `wf_tailwind` Jinja
  globals all follow from a value in that file. `FRAMEWORK_PACKAGE` reads the
  package name off `__name__`, so renaming the distribution needs no edit at
  all. `core/constants.py` keeps the runtime flags and paths and derives its
  own values from the seam.

- `scripts/rebrand.py` — a Typer and questionary workflow that applies a fork's
  identity in one pass. It asks for the eight seam values and the package name,
  previews every rewrite and rename, and then reseats the seam, rewrites the
  sources, renames the package, the asset folder, the abbreviation-named modules
  and the stub tree, and updates both `pyproject.toml` files, the `Dockerfile`
  and `scripts/check_stubs.py`. It reads the current identity out of the seam
  with `ast` instead of importing the framework, so it stays runnable after the
  rebrand it just performed. `--dry-run` prints the plan and writes nothing; a
  dirty working tree aborts unless `--force` is passed. Afterwards it scans for
  leftover mentions of the old brand and reports what it deliberately left
  alone — the class and module vocabulary (`Fluid`, `Ocean`, `Additive` and
  friends), which belongs in an IDE refactor, and the logo assets.

  Verified end to end: rebranding a copy of this repository to `WebAqua` /
  `webaqua` / `aqua` / `wa` / `Lagoon` leaves zero leftovers, and the result
  passes all 93 tests and the stub check unchanged.

### Known limitations

- `TransactionService._fetch` still uses a synchronous database session on the
  `gettext` path, and only for keys explicitly marked uncached. `agettext` now
  offers a non-blocking alternative, but the `{{ _('...') }}` callables
  installed into the Jinja environment stay synchronous on purpose — wiring an
  async `gettext` into the i18n extension is what broke the earliest builds.
- Startup and shutdown hooks run from `Fluid.mix()`, not from the ASGI lifespan
  protocol, so they do not run under an external ASGI server.
- `events.create_signal` and `@events.event` must be called from inside the
  running event loop, because the broadcaster loop is created eagerly.
