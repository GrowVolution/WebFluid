from fastapi.staticfiles import StaticFiles as _StaticFiles

from webfluid.core.constants import (
    APP_STATIC, WF_STATIC,
    FRAMEWORK_ID, FRAMEWORK_ROOT
)

_STATIC = WF_STATIC.lstrip("/")


class CachedStaticFiles(_StaticFiles):
    def __init__(self, *args, max_age=0, **kwargs):
        self.max_age = max_age
        super().__init__(*args, **kwargs)

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        if self.max_age:
            response.headers["cache-control"] = f"public, max-age={self.max_age}"
        return response


class StaticFiles:
    def __init__(self, fluid):
        self._sources = []
        self._max_age = fluid.config["STATIC_MAX_AGE"]

        static = fluid.project_root / _STATIC
        if static.exists():
            self.add(APP_STATIC, static, "static")

        wf_static = f"{FRAMEWORK_ID}_static"
        self.add(WF_STATIC, FRAMEWORK_ROOT / _STATIC, wf_static)
        fluid.jinja_env.globals["wf_static"] = wf_static

    def add(self, path, directory, name=None):
        self._sources.append((
            path,
            CachedStaticFiles(directory=directory, max_age=self._max_age),
            name
        ))

    def mount(self, fluid):
        for path, files, name in self._sources:
            fluid.mount(path, files, name)
