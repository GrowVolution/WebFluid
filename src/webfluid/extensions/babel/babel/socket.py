from fastapi import WebSocket, WebSocketDisconnect
import json

from webfluid.extensions.babel.utils import load_locale, parse_best_match


class Socket:
    _api_whitelist = {
        "gettext", "ngettext",
        "pgettext", "npgettext"
    }

    def __init__(self, babel):
        self.babel = babel

    async def _handle(self, ws):
        from webfluid.extensions.babel.translations import Cache
        while True:
            try:
                msg = json.loads(await ws.receive_text())
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"error": "invalid json"}))
                continue

            for key in {"id", "type", "data"}:
                if key not in msg:
                    await ws.send_text(json.dumps({"error": f"missing '{key}' in message"}))
                    break
            else:
                response = {
                    "id": msg["id"]
                }

                request = msg["type"]
                if request == "cache":
                    locale = str(load_locale(
                        msg["data"].get("locale")
                        or ws.query_params.get("lang")
                        or ws.cookies.get("lang")
                        or parse_best_match(
                            ws.headers.get("Accept-Language", "en-US"),
                            self.babel.supported_locales
                        )
                        or self.babel.default_locale
                    ))

                    cache = Cache.locale_cache(locale)
                    if cache:
                        response["data"] = {
                            "locale": locale,
                            "translations": cache
                        }
                    else:
                        response["error"] = "Cache not found."

                elif request == "translate":
                    fn_name = msg["data"].get("fn", "gettext")
                    if fn_name not in Socket._api_whitelist:
                        response["error"] = "Only (non lazy) gettext api is supported."

                    else:
                        domain = msg["data"].get("domain")
                        fn = getattr(self.babel, f"a{fn_name}")
                        if domain: fn = self.babel.domain_context(domain)(fn)
                        response["data"] = await fn(
                            *msg["data"]["args"],
                            **msg["data"]["variables"]
                        )

                else:
                    response["error"] = f"Unknown request: {request}"

                await ws.send_text(json.dumps(response))

    async def endpoint(self, ws: WebSocket):
        await ws.accept()
        try: await self._handle(ws)
        except WebSocketDisconnect: pass
