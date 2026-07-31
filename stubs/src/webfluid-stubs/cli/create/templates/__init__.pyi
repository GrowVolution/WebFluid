from webfluid.cli.create.templates.main import (
    health_py as health_py,
    tailwind_raw as tailwind_raw,
    vite_base as vite_base,
)
from webfluid.cli.create.templates.project import (
    api_router_py as api_router_py,
    app_v1_py as app_v1_py,
    app_index_html as app_index_html,
    app_index_py as app_index_py,
    app_router_py as app_router_py,
    app_config_py as app_config_py,
    main_py as main_py,
    app_gitignore as app_gitignore,
)
from webfluid.cli.create.templates.additive import (
    api_py as api_py,
    adtv_v1_py as adtv_v1_py,
    adtv_index_html as adtv_index_html,
    adtv_index_py as adtv_index_py,
    app_py as app_py,
    init_py as init_py,
    adtv_gitignore as adtv_gitignore,
)

__all__ = [
    "health_py", "tailwind_raw", "vite_base",

    "api_router_py", "app_v1_py", "app_index_html",
    "app_index_py", "app_router_py", "app_config_py",
    "main_py", "app_gitignore",

    "api_py", "adtv_v1_py", "adtv_index_html",
    "adtv_index_py", "app_py", "init_py", "adtv_gitignore",
]
