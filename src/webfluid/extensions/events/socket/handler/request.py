from webfluid.utils.logging import factory as log_factory


async def request(queries, msg, res):
    data = msg["data"]
    if not isinstance(data, dict):
        res["error"] = "Request data must be a dict."
        return res

    query = data.get("query")
    if not queries.has_query(query):
        res["error"] = f"Query '{query}' does not exist."

    elif queries.is_internal(query):
        res["error"] = f"Query '{query}' is not public."

    if "error" in res: return res

    try: res["data"] = await queries.request(query, data.get("data"))
    except Exception as e:
        log_factory.exception(e)
        res["error"] = f"Query '{query}' failed."
    return res
