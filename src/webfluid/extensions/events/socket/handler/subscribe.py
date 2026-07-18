

def subscribe(socket_manager, events, sid, msg, res):
    event = msg["data"]
    if not events.has_event(event):
        res["error"] = f"Event '{msg['data']}' does not exist."

    elif events.is_internal(event):
        res["error"] = f"Event '{msg['data']}' is not public."

    elif socket_manager.has_subscriptions(event, sid):
        res["error"] = f"Event '{msg['data']}' has already been subscribed."

    if "error" in res: return res

    socket_manager.subscribe(event, sid)
    res["data"] = True
    return res
