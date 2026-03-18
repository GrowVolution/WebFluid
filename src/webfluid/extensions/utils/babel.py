from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from babel import Locale, dates, numbers
from typing import TYPE_CHECKING, Callable, Literal, Any

from webfluid.core.context import FluidContext

if TYPE_CHECKING:
    from webfluid.extensions.babel.constants import DateFormat, DateFormatKey


def parse_best_match(accept_header: str, available: list[str]) -> str | None:
    if not accept_header: return available[0] if available else None

    parsed = []

    for part in accept_header.split(","):
        part = part.strip()
        media, *params = part.split(";")

        q = 1.0
        for p in params:
            p = p.strip()
            if p.startswith("q="):
                try: q = float(p[2:])
                except ValueError: pass

        parsed.append((media.strip(), q))

    parsed.sort(key=lambda x: x[1], reverse=True)

    for media, _ in parsed:
        mtype, msub = media.split("/", 1)

        for candidate in available:
            ctype, csub = candidate.split("/", 1)

            if (
                    (mtype == "*" or mtype == ctype)
                    and
                    (msub == "*" or msub == csub)
            ):
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


def _get_format(
        key: "DateFormatKey",
        format: "DateFormat" = None,
):
    from webfluid.core.ext import babel

    if format is None:
        format = babel.date_formats[key]

    if format in ("short", "medium", "full", "long"):
        return babel.date_formats.get("%s.%s" % (key, format)) or format
    return format


def to_user_timezone(datetime: datetime):
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=timezone.utc)
    tzinfo = get_timezone()
    if tzinfo is None:
        datetime = datetime.replace(tzinfo=timezone.utc)
    return datetime.astimezone(tzinfo)


def to_utc(datetime: datetime):
    return datetime.replace(tzinfo=None)


def format_datetime(
        datetime: datetime | None = None,
        format: "DateFormat" = None,
        rebase: bool = True,
):
    format = _get_format("datetime", format)
    return _date_format(dates.format_datetime, datetime, format, rebase)


def format_date(
        date: datetime | date | None = None,
        format: "DateFormat" = None,
        rebase: bool = True,
):
    if rebase and isinstance(date, datetime):
        date = to_user_timezone(date)
    format = _get_format("date", format)
    return _date_format(dates.format_date, date, format, rebase)


def format_time(
        time: datetime | None = None,
        format: "DateFormat" = None,
        rebase: bool = True,
):
    format = _get_format("time", format)
    return _date_format(dates.format_time, time, format, rebase)


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
        format: str | numbers.NumberPattern | None,
        rebase: bool | None,
        **extra: Any,
):
    locale = get_locale()
    extra = dict(extra) if extra else {}
    if formatter is not dates.format_date and rebase:
        extra["tzinfo"] = get_timezone()
    return formatter(obj, format, locale=locale, **extra)


def format_number(number: float | Decimal | str):
    locale = get_locale()
    return numbers.format_decimal(number, locale=locale)


def format_decimal(
        number: float | Decimal | str,
        format: str | numbers.NumberPattern | None = None,
):
    locale = get_locale()
    return numbers.format_decimal(number, format=format, locale=locale)


def format_currency(
        number: float | Decimal | str,
        currency: str,
        format: str | numbers.NumberPattern | None = None,
        currency_digits: bool = True,
        format_type: Literal["name", "standard", "accounting"] = "standard",
):
    locale = get_locale()
    return numbers.format_currency(
        number,
        currency,
        format=format,
        locale=locale,
        currency_digits=currency_digits,
        format_type=format_type,
    )


def format_percent(number: float | Decimal | str, format: str | None = None):
    locale = get_locale()
    return numbers.format_percent(number, format=format, locale=locale)


def format_scientific(number: float | Decimal | str, format: str | None = None):
    locale = get_locale()
    return numbers.format_scientific(number, format=format, locale=locale)


def fake_t(s: str,  **vars) -> str:
    return s if not vars else s % vars


def fake_tn(s: str, p: str, n: int, **vars) -> str:
    vars.setdefault("n", n)
    return (s if n == 1 else p) % vars
