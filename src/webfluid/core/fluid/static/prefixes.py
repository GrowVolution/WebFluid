from webfluid.core.freeze import Freezable


class StaticPrefixes(Freezable):
    label = "Prefixes"
    closed_after = "initialization"

    def __init__(self, *prefixes):
        super().__init__()
        self._prefixes = set(prefixes)

    def add(self, prefix):
        self.guard()
        self._prefixes.add(prefix)

    def freeze(self, value=None):
        prefixes = tuple(self._prefixes)
        del self._prefixes
        return super().freeze(prefixes)

    def matches(self, path): return path.startswith(self.frozen)
