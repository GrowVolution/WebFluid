from starlette.routing import NoMatchFound


class Routes:
    def __init__(self, fluid):
        self.fluid = fluid
        self._index = {}
        self._unnamed = []
        self._count = -1

    def _build(self):
        index, unnamed = {}, []
        for route in self._flatten(self.fluid.routes):
            name = getattr(route, "name", None)
            if name is None: unnamed.append(route)
            else: index.setdefault(name, []).append(route)

        self._index = index
        self._unnamed = unnamed
        self._count = len(self.fluid.routes)

    @staticmethod
    def _flatten(routes):
        for route in routes:
            contexts = getattr(route, "effective_route_contexts", None)
            if contexts is None: yield route
            else: yield from contexts()

    def url_path_for(self, name, **path_params):
        if self._count != len(self.fluid.routes): self._build()

        for route in (*self._index.get(name, ()), *self._unnamed):
            try: return route.url_path_for(name, **path_params)
            except NoMatchFound: continue

        raise NoMatchFound(name, path_params)
