# WebFluid — Contract

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `18-30` **Application boundary**
- `31-41` **Extension boundary**
- `42-61` **Module boundary**
- `62-75` **Failure and compatibility boundary**
- `76-81` **Documentation maintenance**
- `82-90` **Privacy and security boundary**
<!-- /index -->

The integration boundaries of WebFluid `1.0.0rc1`, for Python 3.14+.
The linked references ship inside this package and provide the detailed contracts.

## Application boundary

| Surface | Contract |
|---------|----------|
| `from webfluid import Fluid, Additive, Manifest, version` | Public application, module and manifest entry points; `version()` reports the installed version. |
| `fluid.prepare_fluid()` | Application-owned factory returning an assembled `Fluid`; migration tooling imports it. |
| `wf run <app>` / `fluid.mix()` | Framework startup and shutdown, including enabled extensions and Additives. An external ASGI server does not run this lifecycle. |
| `app_configs/<app>.ini` | Runtime switches and secrets; keep it out of version control. |
| `fluid/config.py` | Non-secret application configuration and structured values. |

See [project setup](references/project-setup.md) for CLI and configuration,
and [runtime](references/runtime.md) for hooks, context and request processing.

## Extension boundary

Import shared services from `webfluid.core.ext`: `db`, `security`, `events`, `cache`,
`jwt`, `babel`, `mail`, `scheduler`. Enable each required extension in the app configuration;
importing a service does not enable it. Use asynchronous operations in async handlers and
pass `model=` to database executors to select the model's bind.

See [batteries](references/batteries.md) for service APIs, transactions and settings.
Custom framework integrations implement `FluidExtension.expand_fluid` and declare their
entry point as described in [extensions](references/additives.md).

## Module boundary

An Additive owns its manifest, routes, models, services and documentation. Declare dependencies
in `manifest.json`; communicate through documented routes and id-scoped events or queries.
Importing another Additive's implementation or a host application's `fluid.*` ties the package
to that checkout and is unsupported as a reusable integration.

Each reusable package carries its own `.agents/CONTRACT.md` and `.agents/SKILL.md`; `DOCS.md` explains
setup and operation for people. Contracts state what the package provides and consumes;
they must not require documentation from an application that happens to use the package.

A contract is generic. It serves every consumer alike and names none of them: no route, payload
field, configuration key, translation key or special case exists for one package built on top.
A consumer that needs more extends the lower contract generically — a neutral name, an extension
point, a collector — instead of duplicating it, and keeps its own feature semantics above.

See [Additives](references/additives.md) for manifests, enable hooks, routing,
events, documentation and packaging, and [frontend](references/frontend.md)
for templates, static assets and frontend builds.

## Failure and compatibility boundary

Public exports listed in a package's `__all__` follow semantic versioning. Internal modules
are not integration points. Pin the framework version and review release notes on upgrade.
Register hooks during assembly with their documented arity; late or malformed registration
raises instead of silently changing the running application.

Enable-hook exceptions propagate to the Additive registration loop, which logs the failure
and continues with other Additives. Registration is not transactional: work done before a
failure can remain, including routes when `after_enable` fails. A logged failure does not
guarantee that the application stopped or that dependent modules are unavailable.
Run migrations before serving traffic and propagate security-critical initialization errors;
only optional work may be deferred. See [known limitations](references/pitfalls.md).

## Documentation maintenance

Start with [.agents/SKILL.md](SKILL.md) for task-oriented guidance. Every reference
has a line-range index. Run `wf agents index` after edits and `wf agents index --check`
before release to verify these ranges.

## Privacy and security boundary

The request logger and the 500 handler record the method only. `REQUEST_LOG_PATH` (default `DEBUG`),
`REQUEST_LOG_CLIENT` and `REQUEST_LOG_USER_AGENT` (both `False`) opt into one more field each; query
strings are never logged. OAuth popups interpolate HTML-safe JSON, redirects stay on local paths
without backslashes or control characters, and OAuth and CSRF responses carry
`Cache-Control: no-store`. Proxies drop connection-nominated and hop-by-hop headers in both
directions. An integrity reference that cannot refresh reports `unavailable`, never old hashes as
fresh. See [runtime](references/runtime.md) for the logging settings.
