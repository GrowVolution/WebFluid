

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
