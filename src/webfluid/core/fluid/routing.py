from starlette.routing import NoMatchFound


class Routes:
    def __init__(self, fluid):
        self.fluid = fluid
        self._index = {}
        self._count = -1

    def _build(self):
        index = {}
        for route in self.fluid.routes:
            name = getattr(route, "name", None)
            if name is None: continue
            index.setdefault(name, []).append(route)

        self._index = index
        self._count = len(self.fluid.routes)

    def url_path_for(self, name, **path_params):
        if self._count != len(self.fluid.routes): self._build()

        for route in self._index.get(name, ()):
            try: return route.url_path_for(name, **path_params)
            except NoMatchFound: continue

        raise NoMatchFound(name, path_params)
