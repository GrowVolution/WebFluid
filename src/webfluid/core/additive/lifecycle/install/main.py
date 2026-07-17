from .dependencies import resolve_dependencies
from .extract import extract
from .packages import install_packages


def install(additive, _seen=None):
    seen = _seen if _seen is not None else set()
    if additive.id in seen: return
    seen.add(additive.id)

    resolve_dependencies(additive, seen)

    base = additive.base
    if base:
        extract(base)
        install_packages(base)
    extract(additive)
    install_packages(additive)
