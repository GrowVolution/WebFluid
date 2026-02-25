from flask import Blueprint, helpers
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import TYPE_CHECKING, Callable
import signal, os, asyncio

from webfluid.utils import required_arg_count, safe_execute, safe_string
from webfluid.exceptions import EventHookException

if TYPE_CHECKING:
    from types import FrameType


class App:
    def __init__(self, import_name: str):
        self.name = safe_string(os.getenv("APP_NAME", import_name)).lower()
        self.app_root = Path(helpers.get_root_path(import_name)).resolve()
        self.framework_root = Path(__file__).parent.parent.resolve()

        self.app_static = StaticFiles(
            directory=(self.app_root / "static")
        )

        app_path = self.framework_root / "app"
        self.framework_static = StaticFiles(
            directory=(app_path / "static")
        )
        self.framework_templates = Blueprint(
            "fluid", __name__,
            template_folder=(app_path / "templates"),
        )

        self._hooks = {
            "startup": [],
            "shutdown": []
        }
        self._shutdown_flag = asyncio.Event()

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    async def _startup(self):
        for hook in self._hooks["startup"]:
            await safe_execute(hook, EventHookException)

    async def _shutdown(self):
        for hook in reversed(self._hooks["shutdown"]):
            await safe_execute(hook, EventHookException)

    def _handle_shutdown(self, signum: int, frame: "FrameType"):
        if self._shutdown_flag.is_set():
            return
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(self._shutdown_flag.set)

    def startup_hook(self, fn: Callable) -> Callable:
        if required_arg_count(fn) > 0:
            raise TypeError("Startup hooks must not receive non optional arguments.")
        self._hooks["startup"].append(fn)
        return fn

    def shutdown_hook(self, fn: Callable) -> Callable:
        if required_arg_count(fn) > 0:
            raise TypeError("Shutdown hooks must not receive non optional arguments.")
        self._hooks["shutdown"].append(fn)
        return fn

    async def start(self): raise NotImplementedError()

    def enter(self): asyncio.run(self.start())

    @property
    def asgi_app(self): raise NotImplementedError()
