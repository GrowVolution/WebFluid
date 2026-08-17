# The surface: templates, themes and the client

## Template resolution

```python
Environment(
    enable_async=True, auto_reload=DEBUG,
    autoescape=select_autoescape(("html", "htm", "xml", "xhtml", "svg")),
    cache_size=-1
)
```

**Autoescape is on** for those five suffixes and for every `render_string` source. `{{ value }}`
escapes; to emit HTML deliberately, wrap it in `markupsafe.Markup` or pass it through `| safe`. A
template with any other suffix — `.txt`, `.md`, `.json` — is not escaped, so plain-text mail bodies
render as written.

Everything the framework injects is already `Markup`: page sources, `rendered_sources`, theme links,
`frontend()` and `wf_tailwind`. A `str` you build yourself is not — if you assemble HTML in Python
and hand it to a template, wrap it, because joining `Markup` pieces with a plain `str` separator
gives a plain `str` back and it will be escaped.

```python
await fluid.render(template_name, **ctx)     # looked up against the loader stack
await fluid.render_string(source, **ctx)     # compiled from a string, no lookup
```

Both run every registered context processor first. `render_string` is for templates that come from a
database or a user.

> `render()` has **no** `is_string` parameter. Passing one is not an error — it silently becomes an
> ordinary template variable while your source string is looked up as a file name, producing a
> `TemplateNotFound` whose message is your entire template.

### The loader stack

Assembled in this order, searched in this order:

```text
1. fluid/templates/            (your app)        + prefix "app/"
2. additives/<id>/templates/   (each Additive)     prefix "<id>/"  — always prefixed
3. <package>/fluid/templates/  (the framework)   + prefix "fluid/"
```

Your app is searched **before** the framework, so an unprefixed name resolves to your file first and
falls through only when you do not have one. Paths are relative to `fluid/templates` and may nest
arbitrarily.

| Prefix            | Resolves to               | Use it when                                             |
|-------------------|---------------------------|---------------------------------------------------------|
| `app/…`           | `fluid/templates/…`       | You want to be unambiguous                              |
| `fluid/…`         | the framework's templates | You overrode a name locally but still want the original |
| `<additive_id>/…` | that Additive's templates | Always, for Additive templates                          |

**Additive templates are only reachable through their id prefix**, so they can never shadow your
app's names. `additive.render("index.html")` adds the prefix for you. An Additive extending a base
gets a `ChoiceLoader`: its own `templates/` first, then the base's, both under the **child's** id.

### Overriding framework templates

Dropping a file with the same name into `fluid/templates` replaces the framework's. No
configuration.

```html
<!-- fluid/templates/errors/404.html -->
{% extends "fluid/fluid_base.html" %}

{% block content %}
    <h1>{{ _('NOT_FOUND_TITLE') }}</h1>
{% endblock %}
```

Note the `fluid/` prefix on the `extends` — without it, an override of `fluid_base.html` itself would
extend itself and recurse.

The framework ships `fluid_base.html`, `base_email.html`, `base_error.html`, `errors/400.html` …
`errors/503.html` (400, 401, 403, 404, 405, 429, 500, 502, 503) and `errors/debug/500.html`.

Error pages are rendered **only** for a client whose `Accept` header contains `text/html`. Everything
else gets JSON — and outside debug mode that JSON carries nothing but the status text, so a
production 500 cannot hand an API client the SQL fragment the exception happened to contain.

### Adding a loader

```python
fluid.add_template_loader(PrefixLoader({"plugins": FileSystemLoader("/srv/plugins/templates")}))
```

Must be called **before the server comes up** — the stack is frozen in the `_prepare` startup hook,
after which it raises `RuntimeError: Loaders cannot be added after initialization.` Call it during
app assembly or from an extension's `expand_fluid`.

Outside debug mode Jinja does not stat templates, because nothing can change; in debug `auto_reload`
is on. Compiled templates are cached without a size limit.

## The shared context (`WF_PROCESSING`)

`setup_processing(fluid)` installs the context processor that adds these to **every** render, so you
never pass them:

| Variable        | Value                                                                      |
|-----------------|----------------------------------------------------------------------------|
| `url_for`       | `url_for(name, **path_params)` → path; `external=True` → absolute URL      |
| `src`           | `src()` → the injected `<script>` / `<link>` sources, timestamped in debug |
| `theme`         | The active theme's stylesheet link (empty without `WF_THEMES`)             |
| `LANG`          | The active locale                                                          |
| `YEAR`          | Current UTC year                                                           |
| `id`            | `"fluid"` — the framework id                                               |
| `_`, `ngettext` | Babel's, or a no-op fallback when `EXT_BABEL` is off                       |

It also installs a `before_request` logger, the `after_request` hook that swaps in the styled error
pages, the unhandled-exception handler, `GET /wf-identity` and `POST /url-for`.

## `fluid_base.html`

| Block     | Purpose                                                  |
|-----------|----------------------------------------------------------|
| `title`   | Document title. Default `WebFluid App`                   |
| `head`    | Extra `<head>` content — this is where `frontend()` goes |
| `nav`     | The whole `<nav>` body                                   |
| `content` | The page. Almost always the one you fill                 |
| `footer`  | The whole footer body                                    |
| `scripts` | The trailing script block                                |

```html
{% extends "fluid_base.html" %}

{% block title %}{{ _('HOME_TITLE') }}{% endblock %}

{% block head %}
    {{ frontend() if frontend else "" }}
{% endblock %}

{% block content %}
    <section>
        <h1>{{ _('GREETING', name=name) }}</h1>
    </section>
{% endblock %}
```

The head it renders for you: charset, viewport, favicon, `<title>`, the theme link, the Tailwind link
and `src()`.

### Rules for generated templates

- **Extend `fluid_base.html`** unless you have a reason not to. It already wires the theme link, the
  Tailwind link, the injected sources, the locale on `<html lang>` and the favicon.
- **Guard the optional globals** in templates that may render off-request or in an app with a
  different feature set: `{{ frontend() if frontend else "" }}`, `{{ theme if theme else "" }}`.
  `fluid_base.html` does exactly this.
- **Name templates after the route**, mirroring the path: `fluid/templates/admin/users.html` for
  `/admin/users`. Deep nesting is free.
- To replace the base layout wholesale, create `fluid/templates/fluid_base.html` — your app's
  templates are searched first.

## Tailwind and themes

`WF_TAILWIND` compiles every `tailwind_raw.css` it finds in the app's (and the framework's)
`static/css` into a minified `tailwind.css` next to it, and publishes the `wf_tailwind` Jinja global.

```css
/* fluid/static/css/tailwind_raw.css */
@import "tailwindcss" source("../../");

@theme {
    /* your design tokens */
}
```

The `source(...)` argument tells Tailwind where to scan for class names; `../../` from
`fluid/static/css` is `fluid/`, templates included.

**Edit `tailwind_raw.css`, never `tailwind.css`.** The compiled file is overwritten on every boot and
is gitignored.

`WF_THEMES` enables the theme API **and** decides which raw stylesheet name is compiled:
`tailwind_raw.css` when on, `tailwind_no_themes.css` when off.

The shipped theme derives its whole surface from five CSS custom properties on `:root` —
`--wf-blend`, `--wf-deep`, `--wf-veil`, `--wf-sunk`, `--wf-page`. Page and error backgrounds, nav,
footer, dropdowns, cards and traceback frames all read from those with a neutral fallback, so a theme
that only redefines the colour scale already renders coherently.

`window.wf.switchTheme()` (from the injected `base.js`) is the client light/dark preference and is
independent of the server-side theme registry.

## Page sources

```python
app.add_source('<link rel="preconnect" href="https://fonts.googleapis.com">', 10)
app.add_source('<script src="/static/js/analytics.js" type="module"></script>', 5)
```

- **Priority 1–10**, higher first. The framework's own scripts (`base.js`, `i18n.js`, `events.js`)
  use priority 5.
- **Deduplicated by exact string**; a repeat logs a warning and is skipped.
- The HTML is parsed and rejected with `ValueError("Invalid HTML source.")` if it is not a node.
- The list is **frozen** in the `_prepare` startup hook — add sources during app assembly or from an
  Additive's `before_enable`, never later.
- In debug mode every source gets a `?t=<timestamp>` on its `src`/`href`.

## Static files

| Mount                   | Serves                                        | Route name                                |
|-------------------------|-----------------------------------------------|-------------------------------------------|
| `/static`               | `fluid/static` (only if the directory exists) | `static`                                  |
| `/fluid/static`         | the framework's own static                    | `fluid_static` (Jinja global `wf_static`) |
| `/<additive_id>/static` | that Additive's `static/`                     | `<id>_static`                             |
| `/<prefix>/frontend`    | a Vite `dist`                                 | `<name>_frontend`                         |

```html
<script src="{{ url_for('static', path='js/models.js') }}"></script>
<img src="{{ url_for(wf_static, path='img/logo.png') }}" alt="Logo">
```

Everything under a static mount is served with `Cache-Control: public, max-age=STATIC_MAX_AGE` — a
year in production, 0 in debug.

**Keep page behaviour in `fluid/static/js`, one small file per page, loaded with `url_for`.** Inline
`<script>` blocks cannot be cached, linted or reused.

## `APP_FRONTEND`

```python
APP_FRONTEND = {"type": "htmx", "alpine": True}
```

Validated on boot; an invalid block raises `ValueError: Invalid frontend configuration: <reason>`.

| `type`   | Extra keys                                              | Meaning                                                  |
|----------|---------------------------------------------------------|----------------------------------------------------------|
| `"none"` | —                                                       | Pure SSR. `frontend()` still emits the Tailwind link     |
| `"htmx"` | `alpine: bool` (default `False`)                        | SSR plus injected htmx (and optionally Alpine)           |
| `"vite"` | `framework`, `typescript: bool`, `register_index: bool` | A real Vite app served and hot-reloaded by the framework |

`framework` is one of `lit`, `none`, `preact`, `qwik`, `react`, `solid`, `svelte`, `vue`.
`APP_FRONTEND = None` disables the frontend object entirely — no `frontend()` global at all, which is
why templates must guard it.

The same shape is the `frontend` block of an Additive manifest, so every Additive can carry its own
client and they all share one dev server and one build.

**Pick the smallest type that does the job.** Each step up adds a Node toolchain requirement to your
build and your image.

### htmx

```python
APP_FRONTEND = {"type": "htmx", "alpine": True}
```

That is the whole story. htmx and Alpine are served from the framework's own static mount, downloaded
once at project creation. No Node, no build step, no workspace.

### Vite

Three pieces have to line up: a root `package.json` declaring the workspaces
(`"additives/*/frontend"`, `"fluid/frontend"` — the glob is what lets every Additive contribute), a
root `vite.config.js` **written by the framework** (do not hand-write it), and the per-surface
project whose only framework-specific requirement is its `base`:

```js
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/frontend/' : '/vite-dev/',
}))
```

For an Additive the build base is the Additive's prefix, e.g. `'/portal/frontend/'`.

`register_index` defaults to `true`: the framework registers `GET /` and serves the Vite index. Set
it to `false` to own `/` yourself and wire the SPA where you want it:

```python
additive.app.get("/console")(additive.frontend.vite)
```

|            | `wf run app -d`                                                     | `wf run app`                                                                           |
|------------|---------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| Vite       | Dev server on port 5173                                             | Not started                                                                            |
| Serving    | Proxied under `/vite-dev`, HMR live                                 | `dist/` mounted under `/frontend`                                                      |
| index.html | From `frontend/index.html`, srcs rewritten, `@vite/client` injected | From `frontend/dist/index.html`                                                        |
| Build      | —                                                                   | `npm run check/build --workspaces`, gated by `WF_CHECK_FRONTEND` / `WF_BUILD_FRONTEND` |

The served index is post-processed either way: the theme link and every registered source are
injected into its `<head>`, so a Vite app gets the same framework context an SSR page does.

**Do not scaffold a Vite workspace by hand.** `wf create project` and `wf create additive` copy the
right create-vite template, rewrite `package.json` and inject the `base`. And never run npm or vite
through a raw shell in a WebFluid project — use `wf node npm …`.

Turn `WF_CHECK_FRONTEND` and `WF_BUILD_FRONTEND` off in a container image that already built its
assets at image-build time. The `dist` folders are mounted either way.

## The bundled toolchain

Node and the Tailwind CLI are **not** shipped inside the package — they are downloaded on first use
and cached under `webfluid/surface/dist`. A system Node is used when present.

```bash
wf node node --version
wf node npm install
wf node npm run build --workspaces
wf tailwind -- --help          # the -- separator stops Typer parsing the following flags
```

Output is forwarded verbatim; a non-zero exit raises `NodeError`.
