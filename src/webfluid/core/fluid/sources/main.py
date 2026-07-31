from selectolax.lexbor import LexborHTMLParser
from markupsafe import Markup

from webfluid.core.freeze import Freezable
from webfluid.utils.core import check_priority, build_sorted_tuple
from webfluid.utils.logging import factory as log_factory


class Sources(Freezable):
    label = "Sources"

    def __init__(self):
        super().__init__()
        self._sources = {}
        self._seen = set()
        self.rendered = ""

    def add(self, src, priority=1):
        self.guard()
        check_priority(priority)

        node = LexborHTMLParser(src, True).root
        if not node: raise ValueError("Invalid HTML source.")

        if priority not in self._sources:
            self._sources[priority] = []

        if src in self._seen:
            log_factory.warning(f"Source '{src}' already added, skipping...")
            return

        self._sources[priority].append(Markup(src))
        self._seen.add(src)

    def freeze(self, value=None):
        sources = tuple(
            src for group in build_sorted_tuple(self._sources) for src in group
        )
        del self._sources
        del self._seen

        self.rendered = "\n\t".join(sources)
        return super().freeze(sources)

    @property
    def sources(self): return self._frozen
