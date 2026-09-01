from fastapi import WebSocket, WebSocketDisconnect
import json

from webfluid.extensions.babel.utils import load_locale, parse_best_match
from webfluid.utils.logging import factory as log_factory

_KEYS = ("id", "type", "data")


async def _send(ws, response):
    await ws.send_text(json.dumps(response))


async def _receive(ws):
    try: raw = await ws.receive_text()
    except KeyError: return None, "only text frames are supported"

    try: msg = json.loads(raw)
    except json.JSONDecodeError: return None, "invalid json"

    if not isinstance(msg, dict): return None, "message must be an object"

    for key in _KEYS:
        if key not in msg: return None, f"missing '{key}' in message"

    if not isinstance(msg["data"], dict): return None, "data must be an object"

    return msg, None


class Socket:
    _api_whitelist = {
        "gettext", "ngettext",
        "pgettext", "npgettext"
    }

    def __init__(self, babel):
        self.babel = babel

    def _locale(self, ws, data):
        return str(load_locale(
            data.get("locale")
            or ws.query_params.get("lang")
            or ws.cookies.get("lang")
            or parse_best_match(
                ws.headers.get("Accept-Language", "en-US"),
                self.babel.supported_locales
            )
            or self.babel.default_locale
        ))

    async def _dispatch(self, ws, msg):
        from webfluid.extensions.babel.translations import Cache

        response = { "id": msg["id"] }
        data = msg["data"]

        request = msg["type"]
        if request == "cache":
            locale = self._locale(ws, data)

            cache = Cache.locale_cache(locale)
            if cache:
                response["data"] = {
                    "locale": locale,
                    "translations": cache
                }
            else:
                response["error"] = "Cache not found."

        elif request == "translate":
            fn_name = data.get("fn", "gettext")
            if fn_name not in Socket._api_whitelist:
                response["error"] = "Only (non lazy) gettext api is supported."

            else:
                domain = data.get("domain")
                fn = getattr(self.babel, f"a{fn_name}")
                if domain: fn = self.babel.domain_context(domain)(fn)
                response["data"] = await fn(
                    *data.get("args", ()),
                    **data.get("variables", {})
                )

        else:
            response["error"] = f"Unknown request: {request}"

        return response

    async def _handle(self, ws):
        while True:
            msg, error = await _receive(ws)
            if msg is None:
                await _send(ws, { "error": error })
                continue

            try: await _send(ws, await self._dispatch(ws, msg))
            except WebSocketDisconnect: raise
            except Exception as e:
                log_factory.exception(e)
                await _send(ws, {
                    "id": msg["id"],
                    "error": f"Request '{msg['type']}' failed."
                })

    async def endpoint(self, ws: WebSocket):
        await ws.accept()
        try: await self._handle(ws)
        except WebSocketDisconnect: pass
