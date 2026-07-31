from datetime import datetime, UTC

from ..timestamping import timestamped_node
from webfluid.core.constants import THEMES, DEBUG


def get_source_callables(fluid):
    def theme():
        if not THEMES: return ""
        return fluid.get_theme()

    def sources():
        if not DEBUG: return fluid.rendered_sources

        ts = datetime.now(UTC).timestamp()
        return "\n\t".join(
            timestamped_node(src, ts).html for src in fluid.sources
        )

    return theme, sources
