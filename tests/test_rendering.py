from jinja2 import TemplateNotFound
import pytest

from webfluid.core.constants import DEBUG


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


def test_sources_reject_late_additions(make_fluid):
    fluid = make_fluid()
    fluid._sources.freeze()

    with pytest.raises(RuntimeError):
        fluid.add_source('<script src="/late.js"></script>')
