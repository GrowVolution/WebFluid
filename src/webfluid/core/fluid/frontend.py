from markupsafe import Markup

from webfluid.core.constants import TAILWIND, FRAMEWORK_STATIC
from webfluid.core.identity import TAILWIND_GLOBAL
from webfluid.surface.frontend import Frontend
from webfluid.surface.wf_tailwind import generate_tailwind_css
from webfluid.utils.surface import validate_config


def setup_frontend(fluid):
    if fluid.config.get("APP_FRONTEND") is not None:
        result = validate_config(fluid.config["APP_FRONTEND"])
        if not result[0]:
            raise ValueError(f"Invalid frontend configuration: {result[1]}")
        fluid.frontend = Frontend()
        fluid.startup_hook(lambda: fluid.frontend.cover_fluid(fluid))
        fluid.jinja_env.globals["frontend"] = fluid.frontend.include

    if TAILWIND:
        fluid.startup_hook(lambda: generate_tailwind_css(fluid))
        fluid.jinja_env.globals[TAILWIND_GLOBAL] = Markup(
            f'<link rel="stylesheet" href="{FRAMEWORK_STATIC}/css/tailwind.css">'
        )
