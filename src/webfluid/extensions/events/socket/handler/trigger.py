

def trigger(events, msg, res):
    data = msg["data"]
    if not isinstance(data, dict):
        res["error"] = "Request data must be a dict."
        return res

    event = data.get("event")
    if not event:
        res["error"] = "Request data must contain an 'event' key."
        return res

    if not events.has_event(event):
        res["error"] = f"Event '{event}' does not exist."

    elif events.is_internal(event):
        res["error"] = f"Event '{event}' is not public."

    if "error" in res: return res

    events.trigger(event, data.get("data"))
    res["data"] = True
    return res
