# WebFluid — Contract

<!-- index -->
Read this file in parts. Each range is `first-last` as the file stands now — open one with the Read
tool's `offset`/`limit`, or `sed -n 'first,lastp'`.

- `17-29` **Application boundary**
- `30-40` **Extension boundary**
- `41-55` **Module boundary**
- `56-69` **Failure and compatibility boundary**
- `70-74` **Documentation maintenance**
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

See [project setup](.agents/references/project-setup.md) for CLI and configuration,
and [runtime](.agents/references/runtime.md) for hooks, context and request processing.

## Extension boundary

Import shared services from `webfluid.core.ext`: `db`, `security`, `events`, `cache`,
`jwt`, `babel`, `mail`, `scheduler`. Enable each required extension in the app configuration;
importing a service does not enable it. Use asynchronous operations in async handlers and
pass `model=` to database executors to select the model's bind.

See [batteries](.agents/references/batteries.md) for service APIs, transactions and settings.
Custom framework integrations implement `FluidExtension.expand_fluid` and declare their
entry point as described in [extensions](.agents/references/additives.md).

## Module boundary

An Additive owns its manifest, routes, models, services and documentation. Declare dependencies
in `manifest.json`; communicate through documented routes and id-scoped events or queries.
Importing another Additive's implementation or a host application's `fluid.*` ties the package
to that checkout and is unsupported as a reusable integration.

Each reusable package carries its own `CONTRACT.md` and `.agents/SKILL.md`; `DOCS.md` explains
setup and operation for people. Contracts state what the package provides and consumes;
they must not require documentation from an application that happens to use the package.

See [Additives](.agents/references/additives.md) for manifests, enable hooks, routing,
events, documentation and packaging, and [frontend](.agents/references/frontend.md)
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
only optional work may be deferred. See [known limitations](.agents/references/pitfalls.md).

## Documentation maintenance

Start with [.agents/SKILL.md](.agents/SKILL.md) for task-oriented guidance. Every reference
has a line-range index. Run `wf agents index` after edits and `wf agents index --check`
before release to verify these ranges.
