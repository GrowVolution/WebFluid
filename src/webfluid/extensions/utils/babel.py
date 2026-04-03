from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from babel import Locale, dates, numbers
from typing import TYPE_CHECKING, Callable, Literal, Any

from webfluid.core.context import FluidContext

if TYPE_CHECKING:
    from webfluid.extensions.babel.constants import DateFormat, DateFormatKey


def parse_best_match(accept_header: str, available: tuple[str]) -> str | None:
        if not accept_header: return available[0] if available else None

        parsed = []

        for part in accept_header.split(","):
            lang, *params = part.strip().split(";")

            q = 1.0
            for p in params:
                if p.strip().startswith("q="):
                    try: q = float(p.strip()[2:])
                    except ValueError: pass

            parsed.append((lang.strip(), q))

        parsed.sort(key=lambda x: x[1], reverse=True)

        for lang, _ in parsed:
            base = lang.split("-")[0]

            for candidate in available:
                if candidate == lang or candidate == base:
                    return candidate

        return None


def get_locale() -> Locale:
    from webfluid.core.ext import babel

    try: ctx = FluidContext.current()
    except RuntimeError:
        return babel.load_locale(babel.default_locale)

    if babel.locale_selector_fn is not None:
        return babel.load_locale(babel.locale_selector_fn())

    locale = (
        ctx.request.cookies.get("lang")
        or parse_best_match(
            ctx.request.headers.get("Accept-Language"),
            babel.supported_locales
        )
        or babel.default_locale
    )
    return babel.load_locale(locale)


def get_timezone() -> ZoneInfo:
    from webfluid.core.ext import babel

    try: ctx = FluidContext.current()
    except RuntimeError:
        return ZoneInfo(babel.default_timezone)

    if babel.timezone_selector_fn is not None:
        return ZoneInfo(babel.timezone_selector_fn())

    tz = (
        ctx.request.cookies.get("tz") or
        ctx.request.headers.get("X-Timezone") or
        babel.default_timezone
    )
    return ZoneInfo(tz)


def format_message(message: str, **variables: Any) -> str:
    if variables: return message % variables
    return message


def _get_format(
        key: "DateFormatKey",
        fmt: "DateFormat" = None,
):
    from webfluid.core.ext import babel

    if fmt is None:
        fmt = babel.date_formats[key]

    if fmt in ("short", "medium", "full", "long"):
        return babel.date_formats.get("%s.%s" % (key, fmt)) or fmt
    return fmt


def to_user_timezone(dt: datetime):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    tzinfo = get_timezone()
    if tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tzinfo)


def to_utc(dt: datetime):
    return dt.replace(tzinfo=None)


def format_datetime(
        dt: datetime | None = None,
        fmt: "DateFormat" = None,
        rebase: bool = True,
):
    fmt = _get_format("datetime", fmt)
    return _date_format(dates.format_datetime, dt, fmt, rebase)


def format_date(
        d: datetime | date | None = None,
        ftm: "DateFormat" = None,
        rebase: bool = True,
):
    if rebase and isinstance(d, datetime):
        d = to_user_timezone(d)
    ftm = _get_format("date", ftm)
    return _date_format(dates.format_date, d, ftm, rebase)


def format_time(
        t: datetime | None = None,
        fmt: "DateFormat" = None,
        rebase: bool = True,
):
    fmt = _get_format("time", fmt)
    return _date_format(dates.format_time, t, fmt, rebase)


def format_timedelta(
        datetime_or_timedelta: datetime | timedelta,
        granularity: Literal[
            "year", "month", "week", "day", "hour", "minute", "second"
        ] = "second",
        add_direction: bool = False,
        threshold: float = 0.85,
):
    if isinstance(datetime_or_timedelta, datetime):
        datetime_or_timedelta = datetime.now(timezone.utc) - datetime_or_timedelta

    return dates.format_timedelta(
        datetime_or_timedelta,
        granularity,
        threshold=threshold,
        add_direction=add_direction,
        locale=get_locale(),
    )


def _date_format(
        formatter: Callable[..., str],
        obj: datetime | date | time | None,
        fmt: str | numbers.NumberPattern | None,
        rebase: bool | None,
        **extra: Any,
):
    locale = get_locale()
    extra = dict(extra) if extra else {}
    if formatter is not dates.format_date and rebase:
        extra["tzinfo"] = get_timezone()
    return formatter(obj, fmt, locale=locale, **extra)


def format_number(number: float | Decimal | str):
    locale = get_locale()
    return numbers.format_decimal(number, locale=locale)


def format_decimal(
        number: float | Decimal | str,
        fmt: str | numbers.NumberPattern | None = None,
):
    locale = get_locale()
    return numbers.format_decimal(number, format=fmt, locale=locale)


def format_currency(
        number: float | Decimal | str,
        currency: str,
        fmt: str | numbers.NumberPattern | None = None,
        currency_digits: bool = True,
        format_type: Literal["name", "standard", "accounting"] = "standard",
):
    locale = get_locale()
    return numbers.format_currency(
        number,
        currency,
        format=fmt,
        locale=locale,
        currency_digits=currency_digits,
        format_type=format_type,
    )


def format_percent(number: float | Decimal | str, fmt: str | None = None):
    locale = get_locale()
    return numbers.format_percent(number, format=fmt, locale=locale)


def format_scientific(number: float | Decimal | str, fmt: str | None = None):
    locale = get_locale()
    return numbers.format_scientific(number, format=fmt, locale=locale)


def fake_t(s: str,  **args) -> str:
    return s if not args else s % args


def fake_tn(s: str, p: str, n: int, **args) -> str:
    args.setdefault("n", n)
    return (s if n == 1 else p) % args
