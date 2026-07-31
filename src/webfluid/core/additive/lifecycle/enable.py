from webfluid.utils.additives import require_extensions
from webfluid.exceptions import AdditiveException


def _enable(additive, fluid):
    additive.check_enable()
    additive.manifest.check_requirements(fluid.additive_root)

    if additive.base and additive.base.parent:
        raise AdditiveException(
            f"[{additive.name}] Base additive '{additive.base.name}' has already "
            f"been extended by '{additive.base.parent.name}'."
        )
    elif additive.base:
        additive.base.manifest.check_requirements(fluid.additive_root)
        additive.api.include_router(additive.base.api)
        additive.app.include_router(additive.base.app)
        additive.ws.include_router(additive.base.ws)
        additive.base.parent = additive
        additive.base.prefix = additive.prefix
        additive.base.jinja_context["id"] = additive.id

    if additive.frontend is not None:
        additive.frontend.cover_additive(additive)
        additive.jinja_context["frontend"] = additive.frontend.include
        fluid.static_prefixes.add(additive.frontend.prefix)

    additive.jinja_context["id"] = additive.id
    additive._jinja.prepare(fluid)

    fluid.include_router(additive.api, prefix=additive.prefix)
    fluid.include_router(additive.app, prefix=additive.prefix)
    fluid.include_router(additive.ws, prefix=additive.prefix)

    static_path = additive.root_path / "static"
    if static_path.exists():
        static_prefix = f"{additive.prefix}/static"
        fluid.static_files.add(
            static_prefix, static_path,
            f"{additive.id}_static"
        )
        fluid.static_prefixes.add(static_prefix)


def create_enable(additive):

    @require_extensions(*additive.required_extensions)
    async def enable(fluid):
        await additive._lifecycle.run_before(fluid)
        if additive.base: await additive.base._lifecycle.run_before(fluid)

        _enable(additive, fluid)

        await additive._lifecycle.run_after()
        if additive.base: await additive.base._lifecycle.run_after()

    return enable
