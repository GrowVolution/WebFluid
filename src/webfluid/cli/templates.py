###################################################
#               Project Templates                 #
###################################################

api_router_py = """from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

from fluid.api.v1 import v1
api_router.include_router(v1)
"""


app_index_html = """{% extends "fluid_base.html" %}
{# The base example is natively provided by WebFluid. #}

{% block title %}{{ _('Home') }}{% endblock %}

{% block head %}
    {{ frontend() if frontend else "" }}
{% endblock %}

{% block content %}
    <section class="hero">

        <div class="hero-bg">
            <div class="hero-glow hero-glow-primary"></div>
            <div class="hero-glow hero-glow-secondary"></div>
        </div>

        <div class="hero-container">

            <h1 class="hero-title">
                {{ _('My') }}
                <span class="hero-highlight">
                    {{ _('liquified Application') }}
                </span>
            </h1>

            <p class="hero-text">
                {{ _('This is my brand new, super cool WebFluid project.') }}
            </p>

            <div class="hero-actions">
                <a href="https://github.com/GrowVolution/WebFluid"
                   class="hero-button-primary" target="_blank">
                    {{ _('Get Started') }}
                </a>

                <a href="https://github.com/GrowVolution/WebFluid/blob/main/DOCS.md"
                   class="hero-button-secondary" target="_blank">
                    {{ _('Learn More') }}
                </a>
            </div>

            <div class="hero-image">
                <img src="/wf-static/img/banner.jpg" alt="WebFluid Banner">
            </div>

        </div>
    </section>
{% endblock %}"""

app_index_py = """from webfluid.core.context import FluidContext


async def handle_request():
    ctx = FluidContext.current()
    return await ctx.fluid.render("index.html")
"""

app_router_py = """from fastapi import APIRouter
from fastapi.responses import HTMLResponse

app_router = APIRouter(
    default_response_class=HTMLResponse
)

from fluid.app.index import handle_request as index
app_router.get("/")(index)
"""


app_config_py = """from webfluid.core.config import register_config


@register_config(10)
class Config:
    APP_CONFIG = {{
        "title": "{name}",
        "version": "1.0.0"
    }}
    APP_FRONTEND = {frontend}
"""


main_py = """from webfluid import Fluid


def create_app() -> Fluid:
    app = Fluid(__name__)

    from fluid.api import api_router
    app.include_router(api_router)

    from fluid.app import app_router
    app.include_router(app_router)

    return app


if __name__ == "__main__":
    fluid = create_app()
    fluid.mix()
"""


gitignore = """[folders]
.vscode/
.idea/
.venv/
__pycache__/
app_configs/
services/
additives/
instance/
migrations/
translations/
dist/
logs/

[files]
messages.pot
tailwind.css"""


###################################################
#               Additive Templates                #
###################################################

api_py = """from .v1 import v1

__all__ = ["v1"]
"""

adtv_index_html = """{{% extends "fluid_base.html" %}}
{{# The base example is natively provided by WebFluid. #}}

{{% block title %}}{{{{ _('{name}') }}}}{{% endblock %}}

{{% block head %}}
    {{{{ frontend() if frontend else "" }}}}
{{% endblock %}}

{{% block content %}}
    <div class="page-center">
        <div class="page-card">

            <div class="flex flex-col items-center gap-2">

                <div class="text-2xl opacity-80">
                    🧪
                </div>

                <h1 class="page-title">
                    {{{{ _('Adding a new Liquid') }}}}
                </h1>

                <p class="page-text">
                    {{{{ _('Experimenting with spicy Additives.') }}}}
                </p>

            </div>

            <div class="page-divider"></div>

            <div class="mt-2">
                {{% block page_content %}}{{% endblock %}}
            </div>

        </div>
    </div>
{{% endblock %}}"""

adtv_index_py = """

async def handle_request():
    from .. import additive
    return await additive.render("index.html")
"""

app_py = """from .index import handle_request as index

__all__ = ["index"]
"""

init_py = """from webfluid import Additive
{import_base}
additive = Additive(
    __name__,{base}{requirements}
)


@additive.before_enable
def before_enable(_):
    from .api import v1
    additive.api.include_router(v1)

    from .app import index
    additive.app.get("/")(index)
"""


###################################################
#               Shared Templates                  #
###################################################

health_py = """from webfluid.utils.framework import async_result
from datetime import datetime, UTC


async def handle_request():
    return await async_result({
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat()
    })
"""

v1_py = """from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")

from .health import handle_request as health
v1.get("/health")(health)
"""


tailwind_raw = """@import "tailwindcss" source("../../");

@theme {
    /* ... */
}"""


vite_base = """
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
})
"""
