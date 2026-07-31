from webfluid.core.identity import (
    FRAMEWORK_ID, FRAMEWORK_NAME, FRAMEWORK_PACKAGE,
    FRAMEWORK_SITE, FRAMEWORK_DOCS,
    BASE_TEMPLATE, STATIC_GLOBAL
)

api_router_py = f"""from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

from {FRAMEWORK_ID}.api.v1 import setup as setup_v1
setup_v1(api_router)
"""


app_v1_py = """from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")


def setup(router: APIRouter):
    # TODO: Add your API routes here.

    router.include_router(v1)
"""


app_index_html = f"""{{% extends "{BASE_TEMPLATE}" %}}
{{# The base example is natively provided by {FRAMEWORK_NAME}. #}}

{{% block title %}}{{{{ _('Home') }}}}{{% endblock %}}

{{% block head %}}
    {{{{ frontend() if frontend else "" }}}}
{{% endblock %}}

{{% block content %}}
    <section class="hero">

        <div class="hero-bg">
            <div class="hero-glow hero-glow-primary"></div>
            <div class="hero-glow hero-glow-secondary"></div>
        </div>

        <div class="hero-container">

            <h1 class="hero-title wf-rise">
                {{{{ _('My') }}}}
                <span class="hero-highlight">
                    {{{{ _('liquified Application') }}}}
                </span>
            </h1>

            <p class="hero-text wf-rise wf-d1">
                {{{{ _('This is my brand new, super cool {FRAMEWORK_NAME} project.') }}}}
            </p>

            <div class="hero-actions wf-rise wf-d2">
                <a href="{FRAMEWORK_SITE}"
                   class="btn btn-primary" target="_blank">
                    {{{{ _('Get Started') }}}}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                </a>

                <a href="{FRAMEWORK_DOCS}"
                   class="btn btn-ghost" target="_blank">
                    {{{{ _('Learn More') }}}}
                </a>
            </div>

            <div class="hero-image wf-rise wf-d3">
                <img src="{{{{ url_for({STATIC_GLOBAL}, path='img/banner.jpg') }}}}" alt="{FRAMEWORK_NAME} Banner">
            </div>

        </div>
    </section>
{{% endblock %}}"""


app_index_py = f"""from {FRAMEWORK_PACKAGE}.core.context import FluidContext


async def handle_request():
    ctx = FluidContext.current()
    return await ctx.fluid.render("index.html")
"""


app_router_py = f"""from fastapi import APIRouter
from fastapi.responses import HTMLResponse

app_router = APIRouter(
    default_response_class=HTMLResponse
)

from {FRAMEWORK_ID}.app.index import handle_request as index
app_router.get("/")(index)
"""


app_config_py = f"""from {FRAMEWORK_PACKAGE}.core.config import register_config

# The MyConfig class is our convention for developing public git repos.
try: from {FRAMEWORK_ID}._my_config import MyConfig
except ImportError:
    class MyConfig: pass

@register_config(10)
class Config(MyConfig):
    APP_CONFIG = {{{{
        "title": "{{name}}",
        "version": "1.0.0"
    }}}}
    APP_FRONTEND = {{frontend}}
"""


main_py = f"""from {FRAMEWORK_PACKAGE} import Fluid


def prepare_fluid() -> Fluid:
    app = Fluid(__name__)

    from {FRAMEWORK_ID}.api import api_router
    app.include_router(api_router)
    {{index}}
    return app


if __name__ == "__main__":
    fluid = prepare_fluid()
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
