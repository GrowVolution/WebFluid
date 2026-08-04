# Pitfalls: live defects and the traps that produce silently wrong code

Treat the first section as part of the API. Generating code that trips one of these produces a
program that looks right and behaves wrong.

Check the installed version before trusting anything here:

```bash
python -c "from webfluid import version; print(version())"
```

The published docs at `docs.webfluid.dev/latest` track the latest **released** version. When the
installed package is newer, the package's own `CHANGELOG.md` is the authority on the delta — its
*Known limitations* section is the current list.

---

## Live defects (as of `1.0.0b3`)

### Runtime and lifecycle

- **Hooks do not run under an external ASGI server.** Startup and shutdown hooks run from
  `fluid.mix()`, not through the ASGI lifespan protocol. `uvicorn main:fluid` or `gunicorn` skips
  table creation, the scheduler, Additive registration, the frozen loader stack and the static
  mounts. **Run apps through `wf run`.** Your container entrypoint must be `wf run <app>`.
- **Streaming responses skip `after_request` processors.** The request middleware buffers so
  processors can rewrite the body, and gives that up the moment the app announces `more_body`. A
  buffered response also keeps the app's `Content-Length` — a processor that changes the body must
  return a **new** response rather than mutating the one it was handed.
- **`additive.after_request` does not receive a `Response`.** It runs inside the router's endpoint
  wrapper, before FastAPI serialises anything, so it receives whatever the handler returned (a dict,
  a model, a string). `fluid.after_request` *does* receive a real `Response`.
- **`RATELIMIT_DEFAULT` never applies.** slowapi evaluates application-wide defaults only from its
  own middleware, which the framework does not install. An undecorated route is never checked, and
  `@fluid.limit(...)` replaces the defaults rather than adding to them. **Put the limit on the
  route.**

### Data

- **`wf migrate init` picks its template from `SQLALCHEMY_BINDS` in the config, at init time.** Binds
  attached at runtime via `Model.set_bind` — which is how `SECURITY_MODELS_DB_BIND`,
  `BABEL_DATABASE_BIND` and most Additives do it — are invisible to it. Declare them in
  `SQLALCHEMY_BINDS` before running `init`, or enroll the `multi_db` template by hand.

### Auth and tokens

- **JWT signing keys live in the cache**, and a rotation runs as a startup hook. With
  `CACHE_TYPE = legacy` (in-process) every restart mints a new key and forgets the old ones, so every
  previously issued token stops decoding. **Run JWT against Redis.**

### Events

- **Event delivery is best-effort.** Broadcasts use a bounded per-listener buffer sized by
  `EVENTS_EVENT_QUEUE_SIZE` (default 5); a slow consumer loses its oldest events, logged as a
  warning. Fine for dashboards and live notifications, wrong for anything that must not be lost — use
  the database plus a query for that.
- **Registering a *new* event outside a running loop *after* startup raises `FrameworkException`.**
  Before startup it is queued and wired up by a startup hook, so import-time declaration works — but
  nothing will ever drain a channel created after the fact.

### i18n

- **Uncached translations block.** A key explicitly opted out of the cache is read through a
  synchronous session on the `gettext` path. `agettext` is the non-blocking alternative; the Jinja
  callables stay synchronous on purpose. Keep uncached keys off hot paths.

### Tooling

- **HMR rides on a proxied websocket that can die.** A Vite restart is the usual trigger; the
  affected frontend then silently stops picking up changes. A browser refresh re-establishes it —
  no need to restart `wf run`.
- **App configs written before `1.0.0b3` on a non-UTF-8 console** read back correctly on the machine
  that wrote them, but a non-ASCII value in one cannot be recovered elsewhere. Rewrite the affected
  configs once, or keep values ASCII and move secrets behind the `*_FILE` indirection.

## Fixed in `1.0.0b3` — the published `1.0.0b2` docs are stale here

If you are reading `/latest/` and it still describes `1.0.0b2`, these entries no longer apply:

| The b2 docs say                                                                    | `1.0.0b3`                                                                                           |
|------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| `database_uris` rewrites the scheme word everywhere in a URI                       | Only the leading scheme prefix is replaced                                                          |
| `mail.send()` talks plaintext against an implicit-TLS server                       | The sync client opens `SMTP_SSL`; defaults are 587 + STARTTLS; setting both flags raises at startup |
| A refused SMTP greeting escapes as a raw `smtplib` error                           | Connect, STARTTLS and login happen inside the `try`, so both clients raise `FrameworkException`     |
| `app_configs/<name>.ini` is written in the locale encoding                         | Written as UTF-8, read with a locale fallback                                                       |
| A non-numeric `sub` makes `resolve_bearer` answer 500                              | Rejected as an unusable token → the request falls through to 401                                    |
| An unknown `kid` raises a raw `TypeError`                                          | Raises `jwt.InvalidTokenError("Unknown key id.")`                                                   |
| `url_for` is `None` outside a request                                              | Resolves through the application's route table; `external=True` prefixes `BASE_URL`                 |
| A translation equal to its source is read as a miss                                | Hit and miss are reported separately; identity translations work                                    |
| `events.create_signal` at import time raises `RuntimeError: no running event loop` | Queued and wired up from a startup hook                                                             |

Two of those rules survive their fix and are still worth following: **put the user's primary key in
`sub`** (a non-numeric subject is now a 401 rather than a 500, but still never authenticates), and
**use symbolic `SCREAMING_SNAKE` translation keys** (they were always the right shape).

---

## Traps that are not bugs

These are correct behaviour that reliably produces wrong code when assumed away.

### Configuration

- **Two `.ini` sections declaring the same key silently collide.** Every section is flattened into
  one environment mapping. Keep keys unique across the whole file.
- **`[dev]` must be last.** The CLI iterates sections in file order and `[dev]` overwrites what came
  before it.
- **`wf migrate` does not apply `[dev]`.** It reads every section unconditionally. Use a separate app
  config for a development database.
- **Never restate a framework default at the call site.** `fluid.config` carries every key
  `DefaultConfig` declares, so `config.get("SESSION_COOKIE_SECURE", not debug)` is a second source of
  truth. Index framework keys; use `get()` only for keys you invented.
- **`SECURITY_PASSWORD_REQUIREMENTS` is merged, not replaced.** Each class is read with a fallback of
  1, so a class you omit from your dictionary still demands one character. Set it to `0` explicitly
  to drop it.
- **`app_configs/` and `additives/` are gitignored.** `git status` shows nothing after you edit an
  Additive in place. Verify those changes by reading files or compiling them, not by diffing.

### Templates and rendering

- **Autoescape is off.** Values are inserted verbatim. Escape untrusted values (`{{ value | e }}`) or
  wrap known-safe HTML in `markupsafe.Markup`.
- **`render()` has no `is_string` flag.** Passing one is not an error — it silently becomes a
  template variable while your source string is looked up as a file name, and you get a
  `TemplateNotFound` naming the whole template. Use `render_string`.
- **Without `WF_PROCESSING` there is no `url_for`, `theme`, `src` or `_()`**, so `fluid_base.html`
  renders a broken document and every error is a bare JSON body. Turn it on for anything serving
  HTML.
- **Guard optional globals** in templates that may render off-request or in an app with a different
  feature set: `{{ frontend() if frontend else "" }}`.
- **An override of `fluid_base.html` must `extends "fluid/fluid_base.html"`** — without the prefix it
  extends itself and recurses.
- **A single registered `after_request` processor buffers every response in the app.** Register one
  only when you need it, and prefer one that only touches headers.

### Database

- **Mutating an object after its executor block is a silent no-op.** No session is watching, so
  nothing is flushed.
- **Unloaded relationships raise after the block**, they do not return empty. `expire_on_commit` is
  `False`, so columns survive — anything needing a query does not. Use `selectinload` inside the
  block.
- **`user.roles` raises even inside a session** (`lazy="raise_on_sql"`), as do `user.identities`,
  `user.backup_codes`, `role.users`, `role.permissions` and every reverse side. Only
  `user.totp_secret` and `user.webauthn_credentials` are `selectin`.
- **`scalars=True` is the default and is wrong for aggregates.** `select(func.count(...))` needs
  `scalars=False` and then `.scalar()`.
- **Omitting `model=` on an executor call** works until the first model on a non-default bind, then
  silently connects to the wrong database.
- **Do not mix `create_all` with migrations** on the same database. Pick one; for anything you
  deploy, pick migrations.
- **Autogenerate misses column renames** (it emits drop + add, losing data), some server-default
  changes and type changes it considers equivalent. Read every revision before applying it.

### Events and cache

- **The `internal` defaults are asymmetric**: `create_signal` defaults to `internal=False` (public),
  `event` to `internal=True` (server-only). Declaring a signal public and then registering a handler
  without `internal=False` raises `ValueError`. Pass the flag consistently for a given name.
- **`trigger()` gives you nothing** — not even a delivery guarantee. Use a query when you need a
  value back.
- **Redis returns everything as `str`; legacy returns what you put in.** `int(cached)` or
  `json.loads(cached)` is the only shape that works on both.
- **`cache.clear()` is `flushdb`.** Never call it in an app that uses JWT — it drops `jwt:current`
  and every `jwt:<kid>`, invalidating every token in circulation.
- **`CACHE_TYPE = legacy` is wrong with more than one worker** and wrong for `EXT_JWT`.

### Mail

- **`body` is a mapping of MIME subtype → content, not a string.** `mail.send(to, subject, "hello")`
  produces a message with one part per character, because the code iterates `body.items()`.
- **Sync and async clients do not mix.** `mail.send()` inside an `async_client()` block sees a
  context whose `is_async` is `True`, treats it as no context, and opens its own connection.
- **A `fake_async=True` send raises inside its thread**, where nothing catches it. Prefer `asend`.

### Additives

- **Importing another Additive welds them together.** Only strings may cross the boundary — use
  id-scoped events and queries.
- **A top-level `from .. import additive` in a handler module is a circular import.** Import inside
  the handler function.
- **Routes registered after `before_enable` are never mounted.**
- **A base may be extended by exactly one Additive at a time.** If two enabled Additives extend the
  same base, enabling the second fails. Need a shared service? Write an extension.
- **Installing does not enable.** Add the id to `[additives]` and set `WF_ADDITIVES = 1`.
- **`events.request` raises `ValueError` for an unknown name.** An optional dependency needs
  `events.has_query(name)` or a `try`/`except`.
- **Never pass an ORM instance across a contract.** It is detached, its relationships raise, and the
  consumer would need your models.

### Process model

- **One process per app.** `wf run` has no worker model; the event bus, the legacy cache and the
  scheduler are all in-process. Several containers means several event buses, several legacy caches,
  and the scheduler firing once per process. Give the scheduler its own single-instance app config.
- **A scheduled job has no request.** `FluidContext.current()` raises. Use `try_current()`.
- **The log factory is silent unless `IN_EXECUTION` is set**, which only `wf run` does. A log call
  from a script, a `python -c` or a pytest run is dropped.
- **`webfluid.core.constants` is a snapshot read at import time.** Changing `os.environ` afterwards
  changes nothing — use `webfluid.utils.enabled(key)` for a dynamic read.
- **A `FluidContext` is always truthy**, even when empty. Test `try_current()` against `None`.
- **Never deploy with `-d`.** It disables the secure session cookie, disables static caching, and
  puts exception messages and tracebacks into API responses.
