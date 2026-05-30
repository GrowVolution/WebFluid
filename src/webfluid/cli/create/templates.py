###################################################
#               Project Templates                 #
###################################################

api_router_py = """from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

from fluid.api.v1 import setup as setup_v1
setup_v1(api_router)
"""

app_v1_py = """from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")


def setup(router: APIRouter):
    # TODO: Add your API routes here.
    
    router.include_router(v1)
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

            <h1 class="hero-title wf-rise">
                {{ _('My') }}
                <span class="hero-highlight">
                    {{ _('liquified Application') }}
                </span>
            </h1>

            <p class="hero-text wf-rise wf-d1">
                {{ _('This is my brand new, super cool WebFluid project.') }}
            </p>

            <div class="hero-actions wf-rise wf-d2">
                <a href="https://webfluid.dev/"
                   class="btn btn-primary" target="_blank">
                    {{ _('Get Started') }}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                </a>

                <a href="https://docs.webfluid.dev/latest/"
                   class="btn btn-ghost" target="_blank">
                    {{ _('Learn More') }}
                </a>
            </div>

            <div class="hero-image wf-rise wf-d3">
                <img src="{{ url_for(wf_static, path='img/banner.jpg') }}" alt="WebFluid Banner">
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
    {index}
    return app


if __name__ == "__main__":
    fluid = create_app()
    fluid.mix()
"""


app_gitignore = """[folders]
.vscode/
.idea/
.venv/
__pycache__/
node_modules/
app_configs/
app_services/
additives/
migrate/
translations/
dist/
logs/

[files]
messages.pot
tailwind.css
_my_config.py
package-lock.json
*.db"""


###################################################
#               Additive Templates                #
###################################################

api_py = """from .health import handle_request as health
from .v1 import setup as setup_v1

__all__ = [
    "health",
    "setup_v1"
]
"""

adtv_v1_py = """from fastapi import APIRouter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid import Additive

v1 = APIRouter(prefix="/v1")


def setup(a: "Additive"):
    # TODO: Add your API routes here.
    
    a.api.include_router(v1)
"""

adtv_index_html = """{{% extends "fluid_base.html" %}}
{{# The base example is natively provided by WebFluid. #}}

{{% block title %}}{{{{ _('{name}') }}}}{{% endblock %}}

{{% block head %}}
    {{{{ frontend() if frontend else "" }}}}
{{% endblock %}}

{{% block content %}}
    <div class="page-center">
        <div class="page-card wf-rise">

            <div class="flex flex-col items-center gap-2 text-center">

                <div class="error-icon text-2xl">
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
    {index}"""

adtv_gitignore = """[folders]
.vscode/
.idea/
node_modules/
translations/
dist/

[files]
frontend/README.md
frontend/_gitignore
messages.pot
tailwind.css
_my_config.py"""


###################################################
#               Shared Templates                  #
###################################################

health_py = """from datetime import datetime, UTC


def handle_request():
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat()
    }
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
