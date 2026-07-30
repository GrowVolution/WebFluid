import asyncio

from webfluid.utils.core import required_arg_count, safe_execute
from webfluid.exceptions import FrameworkException


class Queries:
    def __init__(self, ctx_decorator):
        self._ctx_decorator = ctx_decorator
        self._queries = {}

    def query(self, name, singleton=True, internal=True):
        if singleton and name in self._queries:
            raise ValueError(f"Query '{name}' already exists.")

        elif not singleton and name in self._queries and self._queries[name]["singleton"]:
            raise ValueError(f"Singleton query '{name}' already exists.")

        if name not in self._queries:
            self._queries[name] = {
                "singleton": singleton,
                "internal": internal,
                "handlers": []
            }

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException("Query handlers must receive exactly one argument (data).")
            self._queries[name]["handlers"].append(self._ctx_decorator(fn))
            return fn
        return decorator

    async def request(self, query, data=None):
        if query not in self._queries:
            raise ValueError(f"Query '{query}' does not exist.")

        tasks = [
            safe_execute(fn, True, query, data)
            for fn in self._queries[query]["handlers"]
        ]
        results = await asyncio.gather(*tasks)
        return results[0] if self._queries[query]["singleton"] else results

    def has_query(self, query):
        return query in self._queries

    def is_singleton(self, query):
        return self.has_query(query) and self._queries[query]["singleton"]

    def is_internal(self, query):
        return self.has_query(query) and self._queries[query]["internal"]

    def handlers(self, query):
        if self.has_query(query):
            return self._queries[query]["handlers"]
        return []
