from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from contextvars import ContextVar
from functools import wraps
from typing import Callable
import traceback, sys, logging, typer

from webfluid.core.context import BaseContext
from webfluid.utils import enabled, async_result


class _LogContext(BaseContext):
    ctx = ContextVar("utils.logging")
    def __init__(self, logger_name: str):
        self.logger = logger_name


class _Formatter(logging.Formatter):

    FORMATS = {
        DEBUG: {"fg": typer.colors.CYAN},
        INFO: {"fg": typer.colors.GREEN},
        WARNING: {"fg": typer.colors.YELLOW},
        ERROR: {"fg": typer.colors.RED, "bold": True},
        CRITICAL: {"fg": typer.colors.RED, "bg": typer.colors.WHITE}
    }

    def __init__(self):
        fmt = "[WF]\t[%(asctime)s] [%(levelname)s]\t%(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S %z"
        super().__init__(fmt, datefmt)
        self.simple_formatter = logging.Formatter(fmt, datefmt)

    def format(self, record: logging.LogRecord):
        msg = super().format(record)
        style_kwargs = self.FORMATS.get(record.levelno, self.FORMATS[INFO])
        return typer.style(msg, **style_kwargs)


class LogFactory:
    def __init__(self):
        self._execution = False
        self.formatter = _Formatter()

        self.colored_console = logging.StreamHandler(sys.stdout)
        self.colored_console.setLevel(logging.NOTSET)
        self.colored_console.setFormatter(self.formatter)

        self.console = logging.StreamHandler(sys.stderr)
        self.console.setLevel(logging.NOTSET)
        self.console.setFormatter(self.formatter.simple_formatter)

        self.main_logger = "fluid"
        self.adtv_logger = "fluid.additives"

    def additive_context(self, fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            async with _LogContext(self.adtv_logger):
                return await async_result(fn(*args, **kwargs))
        return wrapper

    def log(self, message: str, category: int = INFO):
        if not self._execution: return
        self.logger.log(category, message)

    def debug(self, message: str): self.log(message, DEBUG)
    def warning(self, message: str): self.log(message, WARNING)
    def error(self, message: str): self.log(message, ERROR)
    def critical(self, message: str): self.log(message, CRITICAL)

    def exception(self, exc: Exception, message: str = None):
        msg = f"{message.strip()}\n" if message else ""
        tb_str = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        self.error(f"{msg}{type(exc).__name__}: {exc}\n{tb_str.strip()}")

    def start_session(self, loglevel: str = "info"):
        self._execution = enabled("IN_EXECUTION")
        if not self._execution: return

        loglevel = loglevel.upper()
        level = getattr(logging, loglevel, INFO)

        def init_logger(name: str, propagate: bool = False):
            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.propagate = propagate
            logger.handlers.clear()
            logger.addHandler(self.colored_console)
            logger.addHandler(self.console)

        init_logger(self.main_logger, True)
        init_logger(self.adtv_logger)

        self.log("Mixing your WebFluid application.")

    @property
    def logger(self):
        ctx = _LogContext.current()
        logger = ctx.logger if ctx else self.main_logger
        return logging.getLogger(logger)


factory = LogFactory()
