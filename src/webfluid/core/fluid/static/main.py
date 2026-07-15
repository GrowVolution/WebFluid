from fastapi.staticfiles import StaticFiles as _StaticFiles

from webfluid.core.constants import (
    APP_STATIC, WF_STATIC,
    FRAMEWORK_ID, FRAMEWORK_ROOT
)


class StaticFiles:
    def __init__(self, fluid):
        self._sources = []
        static = fluid.app_root / WF_STATIC
        if static.exists():
            self.add(APP_STATIC, static, "static")

        wf_static = f"{FRAMEWORK_ID}_static"
        self.add(WF_STATIC, FRAMEWORK_ROOT / WF_STATIC, wf_static)
        fluid.jinja_env.globals["wf_static"] = wf_static

    def add(self, path, directory, name=None):
        self._sources.append((path, _StaticFiles(directory=directory), name))

    def mount(self, fluid):
        for path, files, name in self._sources:
            fluid.mount(path, files, name)
