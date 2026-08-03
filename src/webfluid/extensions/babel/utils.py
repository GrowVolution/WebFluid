from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from babel import Locale, UnknownLocaleError, dates, numbers
from functools import lru_cache
import json

from webfluid.core.context import FluidContext


def translation_resolver(path, locale_map):
    def resolver():
        translations = { locale: {} for locale in locale_map }
        for t_file in path.glob("*.json"):
            with t_file.open("r", encoding="utf-8") as f:
                messages = json.load(f)

            message_data = "{}" if t_file.stem == "default" else json.dumps(
                dict(
                    pair.split("-", 1)
                    for pair in t_file.stem.split("_")
                )
            )

            for key, texts in messages.items():
                for locale, index in locale_map.items():
                    if key not in translations[locale]:
                        translations[locale][key] = {}
                    translations[locale][key][message_data] = texts[index]

        return translations
    return resolver


def parse_best_match(accept_header, available):
    if not accept_header: return None

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


@lru_cache(maxsize=512)
def load_locale(locale):
    locale_key = locale.replace("-", "_")
    return Locale.parse(locale_key)


def _try_locale(locale):
    if not locale: return None
    try: return load_locale(locale)
    except (ValueError, TypeError, UnknownLocaleError): return None


def _try_timezone(name):
    if not name: return None
    try: return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError): return None


def _request_locale():
    from webfluid.core.ext import babel

    ctx = FluidContext.try_current()
    request = ctx.request if ctx is not None else None
    if request is None:
        return load_locale(babel.default_locale)

    return (
        _try_locale(request.query_params.get("lang"))
        or _try_locale(request.cookies.get("lang"))
        or _try_locale(parse_best_match(
            request.headers.get("Accept-Language"),
            babel.supported_locales
        ))
        or load_locale(babel.default_locale)
    )


def _request_timezone():
    from webfluid.core.ext import babel

    ctx = FluidContext.try_current()
    request = ctx.request if ctx is not None else None
    if request is None:
        return ZoneInfo(babel.default_timezone)

    return (
        _try_timezone(request.cookies.get("tz"))
        or _try_timezone(request.headers.get("X-Timezone"))
        or ZoneInfo(babel.default_timezone)
    )


def get_locale():
    from webfluid.core.ext import babel

    selector = babel.locale_selector_fn
    if selector is not None:
        locale = selector()
        return locale if isinstance(locale, Locale) else load_locale(locale)

    return FluidContext.cached_or("locale", _request_locale)


def get_timezone():
    from webfluid.core.ext import babel

    selector = babel.timezone_selector_fn
    if selector is not None: return ZoneInfo(selector())

    return FluidContext.cached_or("timezone", _request_timezone)


def format_message(message, **variables):
    if variables: return message % variables
    return message


def _get_format(key, fmt=None):
    from webfluid.core.ext import babel

    if fmt is None:
        fmt = babel.date_formats[key]

    if fmt in ("short", "medium", "full", "long"):
        return babel.date_formats.get("%s.%s" % (key, fmt)) or fmt
    return fmt


def to_user_timezone(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_timezone())


def to_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_timezone())
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def format_datetime(dt=None, fmt=None, rebase=True):
    fmt = _get_format("datetime", fmt)
    return _date_format(dates.format_datetime, dt, fmt, rebase)


def format_date(d=None, fmt=None, rebase=True):
    if rebase and isinstance(d, datetime):
        d = to_user_timezone(d)
    fmt = _get_format("date", fmt)
    return _date_format(dates.format_date, d, fmt, rebase)


def format_time(t=None, fmt=None, rebase=True):
    fmt = _get_format("time", fmt)
    return _date_format(dates.format_time, t, fmt, rebase)


def format_timedelta(
        datetime_or_timedelta,
        granularity="second",
        add_direction=False,
        threshold=0.85,
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


def _date_format(formatter, obj, fmt, rebase, **extra):
    locale = get_locale()
    extra = dict(extra) if extra else {}
    if formatter is not dates.format_date and rebase:
        extra["tzinfo"] = get_timezone()
    return formatter(obj, fmt, locale=locale, **extra)


def format_number(number):
    locale = get_locale()
    return numbers.format_decimal(number, locale=locale)


def format_decimal(number, fmt=None):
    locale = get_locale()
    return numbers.format_decimal(number, format=fmt, locale=locale)


def format_currency(
        number,
        currency,
        fmt=None,
        currency_digits=True,
        format_type="standard",
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


def format_percent(number, fmt=None):
    locale = get_locale()
    return numbers.format_percent(number, format=fmt, locale=locale)


def format_scientific(number, fmt=None):
    locale = get_locale()
    return numbers.format_scientific(number, format=fmt, locale=locale)


def fake_t(s, **args):
    return s if not args else s % args


def fake_tn(s, p, n, **args):
    args.setdefault("n", n)
    return (s if n == 1 else p) % args
