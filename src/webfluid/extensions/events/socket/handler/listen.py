

def add_listener(socket_manager, events, sid, msg, res):
    event = msg["data"]
    if not events.has_event(event) or not socket_manager.has_subscriptions(event, sid):
        res["error"] = f"Event '{event}' does not exist or was not subscribed to."
        return res

    socket_manager.add_listener(event, sid, msg["id"])
    return None
