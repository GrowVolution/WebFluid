# WebFluid

A CLI-first, full-stack web framework for Python, built on top of FastAPI.

WebFluid is the framework that powers the WebFluid platform. It keeps FastAPI's
async foundation and adds the pieces you normally have to assemble yourself: an
opinionated project layout, a set of optional built-in extensions (database,
i18n, sessions, caching, mail, and more), a bundled frontend toolchain, and a
package registry called **Ocean** for sharing reusable features between projects.

The framework is currently in beta (`1.0.0b2`) and targets Python 3.14+.

---

## Why it exists

Building a web application in Python usually means wiring together a web layer,
a database, a migration tool, translations, a session and auth story, a caching
layer, a task scheduler, and a frontend build — and then repeating most of that
work on the next project.

WebFluid exists to remove that repetition without hiding the underlying tools.
It is opinionated about *structure* (how a project is laid out, how features are
packaged, how apps are configured and run) while staying close to the libraries
developers already know: FastAPI for the web layer, SQLAlchemy for data, Jinja
for templates, Babel for translations, Alembic for migrations, Vite and Tailwind
for the frontend.

The result is a workflow where a single command scaffolds a project, another
enables the features you need, and a third runs it.

---

## Core ideas

WebFluid is organised around a few concepts. Understanding them is enough to find
your way around the rest of the framework.

| Concept       | What it is                                                                                                                                                                         |
|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Fluid**     | The application object. It extends FastAPI and owns configuration, templating, static files, sessions, and the request lifecycle.                                                  |
| **Additive**  | A self-contained, installable feature module (for example authentication, user accounts, or payments). Additives live in a project's `additives/` package and are enabled per app. |
| **Extension** | A framework-level integration such as the database, translations, or the event bus. Extensions are toggled per app and shared by all additives.                                    |
| **Manifest**  | The `manifest.json` that describes an additive: its id, version, frontend type, and requirements.                                                                                  |
| **Ocean**     | The package registry additives and extensions are published to and installed from, reachable through the `wf ocean` commands.                                                      |
| **Surface**   | The bundled frontend tooling — a managed Node runtime, Vite, and Tailwind.                                                                                                         |

### One project, many apps

A WebFluid project is not tied to a single running application. Instead, a
project defines one or more **app configurations** — small `.ini` files under
`app_configs/` that each decide which extensions, features, and additives are
active. The same codebase can therefore be launched as several distinct apps:

```bash
wf run home     # runs the app defined by app_configs/home.ini
wf run docs     # a different subset of features, same code
wf run ocean    # the full application, with every additive enabled
```

This is how one repository can serve, for instance, a landing page, a
documentation site, and a full product from a shared foundation.

---

## The additive architecture

Additives are the unit of reuse in WebFluid. Each additive is a small package
with its own routers, templates, static assets, optional frontend, and a
manifest.

- **Routers** — every additive exposes an `api` router (JSON, under `/api`), an
  `app` router (HTML pages), and a `ws` router (WebSockets). They are mounted
  under the additive's own prefix so features never collide.
- **Base and default additives** — a *base* additive provides shared building
  blocks with no frontend of its own; a *default* additive can optionally
  *extend* a base to build on top of it. This lets a family of related features
  share a common core.
- **Declared requirements** — a manifest states the WebFluid version an additive
  needs, the other additives it depends on, and any Python packages to install.
  Missing additive dependencies are resolved and pulled from Ocean automatically.
- **Extension requirements** — an additive declares the extensions it relies on
  (for example `sqlalchemy` or `jwt`), and the framework refuses to enable it if
  the host app does not provide them.

Additives are installed into a project rather than imported as libraries, which
keeps their templates and assets editable and their behaviour transparent.

---

## Built-in extensions

Extensions are the "batteries." Each one is optional and enabled per app through
an `EXT_*` flag, so an app only pays for what it uses.

| Extension      | Purpose                                                               |
|----------------|-----------------------------------------------------------------------|
| **SQLAlchemy** | Async database access with support for PostgreSQL, MySQL, and SQLite. |
| **Migrate**    | Alembic-based schema migrations.                                      |
| **Babel**      | Internationalisation and localisation of text, dates, and numbers.    |
| **Security**   | Sessions, roles, and request protection primitives.                   |
| **Events**     | An in-application event bus for decoupling features.                  |
| **Cache**      | Caching backed by Redis or an in-memory store.                        |
| **Mail**       | Asynchronous SMTP email delivery.                                     |
| **JWT**        | Signing and verification of JSON Web Tokens.                          |
| **Scheduling** | Cron and interval background jobs via APScheduler.                    |

Extensions plug their own subcommands into the CLI through the
`webfluid.extensions` entry point group — that is how Babel adds its catalog
commands and Migrate its migration ones — so third parties can ship extensions
that feel like the built-in ones.

---

## The frontend surface

WebFluid manages the frontend toolchain so projects do not have to. The CLI can
download and drive a self-contained Node runtime, scaffold a Vite frontend, and
compile Tailwind — all without a global Node installation.

When scaffolding, you can choose:

- **None** — server-rendered Jinja templates only.
- **HTMX** — progressive enhancement, optionally with Alpine.js.
- **Vite** — a full SPA-style frontend using React, Vue, Svelte, Solid, Preact,
  Lit, or Qwik, with optional TypeScript.

Tailwind and a theming system are available to every app, and each additive can
carry its own independent frontend.

---

## Runtime and stubs

WebFluid is distributed as two packages:

- **`webfluid`** — the runtime. Its public API is exposed through lazy imports so
  that starting the CLI or importing a submodule stays fast, and the runtime
  ships without inline type annotations.
- **`webfluid-stubs`** — a companion distribution of `.pyi` type stubs that
  mirrors the runtime one-to-one. Installing it gives editors and type checkers
  full signatures and documentation without adding any weight to the runtime.

Install both together when you want typing support:

```bash
pip install "webfluid[typing]"
```

---

## API stability

Everything listed in a package's `__all__` follows semantic versioning from
`1.0.0b1` onwards. Anything else — module layout, private attributes, helper
functions that are not exported — is internal and may change in any release.

Breaking changes are listed in [CHANGELOG.md](CHANGELOG.md). Upgrading from
`1.0.0a2` requires changes; the most common one is `Fluid.app_root`, which is
now `Fluid.project_root` and warns when used under the old name. `1.0.0b2`
adds three smaller ones, all in the Babel helpers: `format_date`'s second
parameter is spelled `fmt` rather than `ftm`, `to_utc` converts to UTC instead
of only dropping the offset, and `parse_best_match` reports no match for a
missing `Accept-Language` header instead of picking the first supported locale.

---

## The `wf` command line

The CLI is the primary way to work with WebFluid. A few of the most common
commands:

| Command                               | What it does                                                         |
|---------------------------------------|----------------------------------------------------------------------|
| `wf create project <name>`            | Scaffold a new project, including its frontend tooling.              |
| `wf create additive <id>`             | Scaffold a new additive inside a project.                            |
| `wf create app <name>`                | Generate an app configuration (`.ini`).                              |
| `wf run <app>`                        | Run an app configuration, with optional interactive and debug modes. |
| `wf ocean search / install / publish` | Browse, install, and publish packages on Ocean.                      |
| `wf ocean login / logout`             | Authenticate against Ocean.                                          |
| `wf node …` / `wf tailwind …`         | Drive the bundled frontend tooling.                                  |

Extensions register their own subcommands too — for example, Babel adds
translation extraction and compilation, and Migrate adds migration commands.

---

## A minimal application

```python
from webfluid import Fluid


def prepare_fluid() -> Fluid:
    app = Fluid(__name__)
    # register routers, additives, sources, and hooks here
    return app


if __name__ == "__main__":
    fluid = prepare_fluid()
    fluid.mix()
```

In practice you rarely start from a blank file — `wf create project` generates a
working structure, and `wf run` launches it against a chosen app configuration.

---

## Who it is for

WebFluid is aimed at Python developers building full-stack web applications who
want a clear project structure and reusable features without stepping away from
the FastAPI ecosystem. If you have ever wanted a Flask- or Django-style sense of
"a place for everything" on top of modern async Python, this framework is built
for that.

---

## Where to go next

- **Documentation:** <https://docs.webfluid.dev>
- **Ocean (packages):** <https://ocean.webfluid.dev>

The documentation covers the CLI, the additive contract, each extension, and the
frontend surface in depth. This README is only a starting point — the framework
is meant to be explored.

---

## License

WebFluid is released under the **MIT License**.

It sits within a larger ecosystem where different components carry different
licenses. The authoritative overview is the
[Ocean Licensing page](https://ocean.webfluid.dev/licensing).
