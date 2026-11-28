from jinja2 import TemplateNotFound
from markupsafe import Markup
import pytest

from webfluid.core.constants import DEBUG

PAYLOAD = "<script>alert(1)</script>"


@pytest.mark.asyncio
async def test_render_string_renders_its_source(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    assert await fluid.render_string("{{ value }}", value="x") == "x"


@pytest.mark.asyncio
async def test_is_string_is_a_plain_template_variable(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    assert await fluid.render_string(
        "{{ is_string }}", is_string=True
    ) == "True"

    with pytest.raises(TemplateNotFound):
        await fluid.render("{{ value }}", is_string=True, value="x")


@pytest.mark.asyncio
async def test_context_processors_do_not_override_call_context(make_fluid):
    fluid = make_fluid()
    fluid.context_processor(lambda: { "greeting": "from-processor" })
    await fluid._prepare()

    assert await fluid.render("page.html", greeting="explicit") \
        == "<html><body>explicit</body></html>"


def test_template_autoreload_follows_debug(make_fluid):
    assert make_fluid().jinja_env.auto_reload is DEBUG


def test_sources_are_joined_once(make_fluid):
    fluid = make_fluid()
    fluid.add_source('<script src="/a.js"></script>', priority=2)
    fluid._sources.freeze()

    rendered = fluid.rendered_sources
    assert rendered.count("<script") == 2
    assert rendered.index("base.js") < rendered.index("/a.js")


@pytest.mark.asyncio
async def test_templates_escape_their_context(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    rendered = await fluid.render("page.html", greeting=PAYLOAD)
    assert PAYLOAD not in rendered
    assert "&lt;script&gt;" in rendered


@pytest.mark.asyncio
async def test_render_string_escapes_its_context(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    assert await fluid.render_string("{{ value }}", value=PAYLOAD) \
        == "&lt;script&gt;alert(1)&lt;/script&gt;"


@pytest.mark.asyncio
async def test_markup_is_rendered_verbatim(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    assert await fluid.render_string(
        "{{ value }}", value=Markup('<b class="x">hi</b>')
    ) == '<b class="x">hi</b>'


@pytest.mark.asyncio
async def test_the_safe_filter_still_opts_out(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    assert await fluid.render_string(
        "{{ value | safe }}", value="<b>hi</b>"
    ) == "<b>hi</b>"


@pytest.mark.asyncio
async def test_sources_survive_escaping(make_fluid):
    fluid = make_fluid()
    await fluid._prepare()

    rendered = await fluid.render_string("{{ src }}", src=fluid.rendered_sources)
    assert "&lt;" not in rendered
    assert "<script" in rendered


def test_sources_reject_late_additions(make_fluid):
    fluid = make_fluid()
    fluid._sources.freeze()

    with pytest.raises(RuntimeError):
        fluid.add_source('<script src="/late.js"></script>')


BRAND = """
:root, :root[data-theme="light"] {
    --primary-4: #294A4E;
    --primary-5: #193539;
    --tertiary-3: #BD5B21;
    --accent: var(--tertiary-3);
}

:root[data-theme="dark"] {
    --primary-5: #10282C;
}
"""


def _themes(monkeypatch, enabled=True):
    monkeypatch.setattr("webfluid.core.fluid.sources.themes.THEMES", enabled)
    monkeypatch.setattr("webfluid.core.fluid.jinja.rendering.THEMES", enabled)


def _sheet(project, name, css):
    (project / "fluid" / "static" / "css" / name).write_text(css, encoding="utf-8")


async def _themed(make_fluid, project, monkeypatch, enabled=True):
    _themes(monkeypatch, enabled)
    _sheet(project, "brand.css", BRAND)
    fluid = make_fluid()
    if enabled:
        fluid.add_theme("brand", (
            '<link rel="stylesheet" href="/fluid/static/css/theme.css">\n'
            '<link rel="stylesheet" href="/static/css/brand.css?v=3">'
        ))
        fluid._themes.global_theme = "brand"
    await fluid._prepare()
    return fluid


@pytest.mark.asyncio
async def test_inject_theme_stays_in_the_context_when_themes_are_off(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch, enabled=False)

    assert fluid.theme_variables() == {}
    assert await fluid.render_string("{{ inject_theme }}", inject_theme=True) == "True"
    assert await fluid.render_string("{{ inject_theme }}|{{ theme }}", inject_theme=False, theme="link") \
        == "False|link"


@pytest.mark.asyncio
async def test_inject_theme_true_replaces_theme_with_the_variables(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)

    rendered = await fluid.render_string(
        "{{ inject_theme is defined }}|{{ theme is dict }}|{{ theme['--primary-5'] }}|{{ theme['--accent'] }}",
        inject_theme=True, theme="link"
    )
    assert rendered == "False|True|#193539|#bd5b21"


@pytest.mark.asyncio
async def test_inject_theme_false_keeps_the_supplied_theme(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)
    fluid.context_processor(lambda: { "theme": fluid.get_theme() })

    rendered = await fluid.render_string("{{ inject_theme is defined }}|{{ theme }}", inject_theme=False)
    assert rendered.startswith("False|<link")
    assert "brand.css" in rendered
    assert await fluid.render_string("{{ theme }}", inject_theme=False, theme="mine") == "mine"


@pytest.mark.asyncio
async def test_inject_theme_reaches_file_templates(make_fluid, project, monkeypatch):
    (project / "fluid" / "templates" / "themed.html").write_text(
        "{{ theme.get('--primary-4', '#000000') }}", encoding="utf-8"
    )
    fluid = await _themed(make_fluid, project, monkeypatch)

    assert await fluid.render("themed.html", inject_theme=True) == "#294a4e"
    assert await fluid.render("themed.html", theme={}) == "#000000"


@pytest.mark.asyncio
async def test_inject_theme_reaches_additive_rendering(make_fluid, project, monkeypatch):
    from jinja2 import DictLoader, PrefixLoader
    from types import SimpleNamespace
    from webfluid.core.additive.jinja import Jinja
    from webfluid.core.context.fluid import FluidContext

    _themes(monkeypatch)
    _sheet(project, "brand.css", BRAND)
    fluid = make_fluid()
    fluid.add_theme("brand", '<link rel="stylesheet" href="/static/css/brand.css">')
    fluid._themes.global_theme = "brand"

    additive = SimpleNamespace(id="demo", parent=None)
    jinja = Jinja(additive, PrefixLoader({ "demo": DictLoader({
        "mail.html": "{{ label }}:{{ theme['--tertiary-3'] }}:{{ inject_theme is defined }}"
    }) }))
    jinja.context.add_processor(lambda: { "label": "demo" })
    jinja.prepare(fluid)
    await fluid._prepare()

    with FluidContext(fluid):
        assert await jinja.renderer.render("mail.html", inject_theme=True) == "demo:#bd5b21:False"


@pytest.mark.asyncio
async def test_variables_follow_the_session_theme_and_fall_back_to_the_global_one(make_fluid, project, monkeypatch):
    from types import SimpleNamespace
    from webfluid.core.context.fluid import FluidContext

    fluid = await _themed(make_fluid, project, monkeypatch)
    _sheet(project, "other.css", ":root { --primary-5: #010203; }")
    fluid.add_theme("other", '<link rel="stylesheet" href="/static/css/other.css">')

    assert fluid.theme_variables()["--primary-5"] == "#193539"
    assert fluid.theme_variables("other")["--primary-5"] == "#010203"

    request = SimpleNamespace(session={ "theme": "other" })
    with FluidContext(fluid, request):
        assert fluid.theme_variables()["--primary-5"] == "#010203"
        assert await fluid.render_string("{{ theme['--primary-5'] }}", inject_theme=True) == "#010203"

    with FluidContext(fluid):
        assert fluid.theme_variables()["--primary-5"] == "#193539"


@pytest.mark.asyncio
async def test_variables_layer_overrides_and_schemes(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)

    light = fluid.theme_variables()
    dark = fluid.theme_variables(scheme="dark")
    framework = fluid.theme_variables("fluid")

    assert light["--primary-4"] == "#294a4e" and framework["--primary-4"] == "#253f52"
    assert dark["--primary-5"] == "#10282c" and dark["--primary-4"] == "#213646"
    assert light["--wf-blend"] == "#193539"
    assert light["--wf-page"] == "#14292c"
    assert light["--default-1"] == "#90a1b9"
    assert light["--wf-shadow"] == "0 3px 12px rgba(0, 0, 0, 0.12)"
    assert light["--body"] == '"Inter", system-ui, sans-serif'


@pytest.mark.asyncio
async def test_variables_resolve_references_and_convert_colours(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)
    _sheet(project, "edge.css", """
        :where(:root) { --base: #102030; --soft: color-mix(in srgb, var(--base) 50%, white); }
        html { --base: #000000; }
        :root { --base: #112233 !important; --chain: var(--missing, var(--base)); }
        :root { --loop-a: var(--loop-b); --loop-b: var(--loop-a); --orphan: var(--nowhere); }
        :root { --alpha: #ff000080; --hsl: hsl(120 100% 25%); --ok: oklch(62.8% 0.2577 29.23); }
        :root { --lab: lab(50% 0 0); --pick: light-dark(#ffffff, #000000); }
        :root { --veil: color-mix(in srgb, red 25%, transparent); }
        :root { --name: white; --word: inherit; --empty-fallback: var(--nowhere,); }
        @media (prefers-color-scheme: dark) { :root { --mode: dark; } }
        @media (min-width: 600px) { :root { --wide: 1; } }
        @layer base { :root { --layered: #abcdef; } }
    """)
    fluid.add_theme("edge", '<link rel="stylesheet" href="/static/css/edge.css">')

    values = fluid.theme_variables("edge")
    assert values["--base"] == "#112233"
    assert values["--chain"] == "#112233"
    assert values["--soft"] == "#889099"
    assert "--loop-a" not in values and "--loop-b" not in values and "--orphan" not in values
    assert "--empty-fallback" not in values
    assert values["--alpha"] == "rgba(255, 0, 0, 0.502)"
    assert values["--hsl"] == "#008000"
    assert values["--ok"] == "#ff0000"
    assert values["--lab"] == "#777777"
    assert values["--pick"] == "#ffffff"
    assert values["--veil"] == "rgba(255, 0, 0, 0.25)"
    assert values["--name"] == "#ffffff" and values["--word"] == "inherit"
    assert values["--layered"] == "#abcdef"
    assert "--mode" not in values and "--wide" not in values

    dark = fluid.theme_variables("edge", scheme="dark")
    assert dark["--mode"] == "dark" and dark["--pick"] == "#000000"


@pytest.mark.asyncio
async def test_variables_never_raise(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)
    fluid.add_theme("remote", '<link rel="stylesheet" href="https://cdn.example/theme.css">')
    remote = fluid.theme_variables("remote")
    assert "--primary-1" not in remote and "--wf-page" not in remote
    assert remote["--wf-shadow"] == "0 3px 12px rgba(0, 0, 0, 0.12)"

    def broken(*_): raise OSError("disk gone")
    monkeypatch.setattr(fluid._themes, "_read", broken)
    assert fluid.theme_variables() == {}
    assert await fluid.render_string("{{ theme is dict }}|{{ theme | length }}", inject_theme=True) == "True|0"


@pytest.mark.asyncio
async def test_base_email_has_a_themed_and_a_static_path(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)

    static = await fluid.render("base_email.html", _=str)
    themed = await fluid.render("base_email.html", inject_theme=True, _=str)
    partial = await fluid.render("base_email.html", theme={ "--primary-4": "#123456" }, _=str)

    assert "background-color:#10222f" in static and "background-color:#213646" in static
    assert "var(" not in themed and "color-mix" not in themed
    assert "background-color:#294a4e" in themed and "#213646" not in themed
    assert "background-color:#123456" in partial and "background-color:#10222f" in partial
    assert "background-color:#1c3240" in partial


@pytest.mark.asyncio
async def test_base_email_stays_static_without_themes(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch, enabled=False)

    rendered = await fluid.render("base_email.html", inject_theme=True, _=str)
    assert "background-color:#10222f" in rendered and "background-color:#213646" in rendered


LIGHT = """
:root {
    color-scheme: light;
    --wf-page: #f3f6f5;
    --wf-panel: #ffffff;
    --wf-text: #12292c;
    --wf-muted: #3d5356;
    --wf-caption: #62777a;
    --wf-line: rgba(18, 41, 44, 0.14);
}
"""


def test_contrast_keeps_a_readable_colour_and_replaces_an_unreadable_one():
    from webfluid.core.fluid.jinja.contrast import contrast, is_light, luminance

    assert is_light("#f3f6f5") and is_light("rgba(255, 255, 255, 0.9)") and is_light("#fff")
    assert not is_light("#14292c") and not is_light("inherit") and not is_light(None)
    assert luminance("#000000") == 0 and luminance("not a colour") is None
    assert contrast("#294a4e", "#f0f2f5", "#ffffff", "#10222f") == "#f0f2f5"
    assert contrast("#294a4e", "#12292c", "#ffffff", "#10222f") == "#ffffff"
    assert contrast("#f3f6f5", "#ffffff", "#10222f") == "#10222f"
    assert contrast("#bd5b21", "#f0f2f5", "#ffffff", "#10222f") == "#ffffff"
    assert contrast("unknown", "#123456", "#ffffff") == "#123456" and contrast("#000000") == "#000000"


@pytest.mark.asyncio
async def test_base_email_stays_readable_with_a_light_theme(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)
    _sheet(project, "light.css", LIGHT)
    fluid.add_theme("light", (
        '<link rel="stylesheet" href="/static/css/brand.css">\n'
        '<link rel="stylesheet" href="/static/css/light.css">'
    ))

    dark = await fluid.render("base_email.html", inject_theme=True, with_legal=True, _=str)
    light = await fluid.render("base_email.html", theme=fluid.theme_variables("light"), with_legal=True, _=str)
    static = await fluid.render("base_email.html", with_legal=True, _=str)

    assert 'name="color-scheme" content="dark"' in dark and 'name="color-scheme" content="dark"' in static
    assert 'name="color-scheme" content="light"' in light and "background-color:#f3f6f5" in light
    assert "background-color:#294a4e;color:#ffffff" in light and "color:#12292c" not in light
    assert "background-color:#213646;color:#ffffff" in static


@pytest.mark.asyncio
async def test_base_email_leaves_the_callers_context_names_alone(make_fluid, project, monkeypatch):
    fluid = await _themed(make_fluid, project, monkeypatch)
    names = ("page", "card", "header", "panel", "heading", "text", "muted", "caption", "action", "scheme")
    source = ('{% extends "base_email.html" %}{% block content %}'
              + "|".join("{{ %s }}" % name for name in names) + "{% endblock %}")
    values = {name: f"caller-{name}" for name in names}

    for themed in (True, False):
        rendered = await fluid.render_string(source, inject_theme=themed, _=str, **values)
        assert "|".join(values[name] for name in names) in rendered
