class StaticPrefixes:
    def __init__(self, *prefixes):
        self._prefixes = set(prefixes)
        self._frozen = None

    def add(self, prefix):
        if self._frozen is not None:
            raise RuntimeError("Prefixes cannot be added after initialization.")
        self._prefixes.add(prefix)

    def freeze(self):
        self._frozen = tuple(self._prefixes)
        del self._prefixes

    def matches(self, path):
        if self._frozen is None:
            raise RuntimeError("Prefixes must be frozen before use.")
        return path.startswith(self._frozen)