

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

    res["data"] = await queries.request(query, data.get("data"))
    return res
