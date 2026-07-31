import inspect, asyncio


def required_arg_count(fn):
    sig = inspect.signature(fn)

    return sum(
        1
        for p in sig.parameters.values()
        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        and p.default is inspect._empty
    )


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
