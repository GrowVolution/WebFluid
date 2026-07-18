

def unsubscribe(socket_manager, events, sid, msg, res):
    event = msg["data"]
    if not events.has_event(event) or not socket_manager.has_subscriptions(event):
        res["error"] = f"Event '{event}' does not exist or was not subscribed to."
        return res

    socket_manager.unsubscribe(event, sid)
    res["data"] = True
    return res
