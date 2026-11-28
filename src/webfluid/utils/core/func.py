import asyncio, inspect


RECEIVER_NAMES = frozenset({"self", "cls", "mcs", "metacls"})
POSITIONAL_KINDS = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)


def _parameters(fn):
    if isinstance(fn, (classmethod, staticmethod)):
        fn = fn.__func__
    params = list(inspect.signature(fn).parameters.values())
    if (
        params and not inspect.ismethod(fn)
        and params[0].kind in POSITIONAL_KINDS
        and params[0].name in RECEIVER_NAMES
    ):
        params = params[1:]
    return params


def required_arg_count(fn):
    return sum(
        1
        for p in _parameters(fn)
        if p.kind in (*POSITIONAL_KINDS, inspect.Parameter.KEYWORD_ONLY)
        and p.default is inspect.Parameter.empty
    )


def accepts_arg_count(fn, count):
    params = _parameters(fn)
    if any(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params):
        return False
    positional = [p for p in params if p.kind in POSITIONAL_KINDS]
    required = sum(1 for p in positional if p.default is inspect.Parameter.empty)
    variadic = any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in params)
    return required <= count and (variadic or count <= len(positional))


async def async_result(result):
    if asyncio.iscoroutine(result):
        return await result
    return result


async def safe_execute(fn, reraise, *args, **kwargs):
    try: return await async_result(fn(*args, **kwargs))
    except Exception as e:
        if reraise: raise
        else:
            from ..logging import factory as log_factory
            log_factory.exception(e)
    return None


async def run_in_executor(fn, *args, executor=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fn, *args)
