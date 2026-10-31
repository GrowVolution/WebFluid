from pathlib import Path

from webfluid.extensions.babel.utils import translation_resolver

translations = translation_resolver(
    Path(__file__).parent, {
        "en": 0, "de": 1
    }
)
