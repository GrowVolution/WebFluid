from typing import Literal

from frozendict import frozendict

type DateFormat = Literal["short", "medium", "long", "full"] | str | None

type DateFormatKey = Literal[
    "time",
    "date",
    "datetime",
    "time.short",
    "time.medium",
    "time.full",
    "time.long",
    "date.short",
    "date.medium",
    "date.full",
    "date.long",
    "datetime.short",
    "datetime.medium",
    "datetime.full",
    "datetime.long",
]

DEFAULT_LOCALE: str
DEFAULT_TIMEZONE: str
DEFAULT_DATE_FORMATS: frozendict[DateFormatKey, DateFormat]
