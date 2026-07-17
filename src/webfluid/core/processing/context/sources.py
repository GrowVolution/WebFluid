from datetime import datetime, UTC

from ..timestamping import timestamped_node
from webfluid.core.constants import THEMES, DEBUG


def get_source_callables(fluid):
    def theme():
        if not THEMES: return ""
        return fluid.get_theme()

    def sources():
        def get():
            if not DEBUG: return fluid.sources

            ts = datetime.now(UTC).timestamp()
            timestamped = []
            for src in fluid.sources:
                timestamped.append(timestamped_node(src, ts).html)
            return timestamped
        cached = "\n\t".join(get())
        return "\n\t".join(get()) if DEBUG else cached

    return theme, sources
