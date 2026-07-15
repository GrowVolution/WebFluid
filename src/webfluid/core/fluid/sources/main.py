from selectolax.lexbor import LexborHTMLParser
from markupsafe import Markup

from webfluid.utils.core import check_priority, build_sorted_tuple
from webfluid.utils.logging import factory as log_factory


class Sources:
    def __init__(self):
        self._sources = {}
        self._seen = set()
        self.sources = None

    def add(self, src, priority=1):
        if self.sources is not None:
            raise RuntimeError("Sources cannot be added after the server was started.")

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

    def freeze(self):
        self.sources = tuple()
        for sources in build_sorted_tuple(self._sources):
            self.sources += tuple(sources)
        del self._sources
        del self._seen
