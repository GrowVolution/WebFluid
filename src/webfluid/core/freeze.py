

class Freezable:
    label = "Entries"
    closed_after = "the server was started"

    def __init__(self): self._frozen = None

    @property
    def is_frozen(self): return self._frozen is not None

    @property
    def frozen(self):
        if self._frozen is None:
            raise RuntimeError(f"{self.label} must be frozen before use.")
        return self._frozen

    def guard(self):
        if self._frozen is not None:
            raise RuntimeError(
                f"{self.label} cannot be added after {self.closed_after}."
            )

    def freeze(self, value):
        self.guard()
        self._frozen = value
        return self._frozen
