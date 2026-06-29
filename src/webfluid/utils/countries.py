from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from webfluid.core.context import FluidContext

if TYPE_CHECKING:
    from babel import Locale
    from fastapi import Request


DEFAULT_COUNTRY = "DE"

ISO_3166_1_ALPHA2: tuple[str, ...] = (
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT",
    "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI",
    "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY",
    "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
    "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL",
    "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
    "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
    "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW",
    "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
    "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
    "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF",
    "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW",
    "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
)

_CODE_SET = frozenset(ISO_3166_1_ALPHA2)

Country = StrEnum("Country", {code: code for code in ISO_3166_1_ALPHA2})

_GEO_HEADERS = (
    "CF-IPCountry",
    "X-Country-Code",
    "X-GeoIP-Country",
    "X-GeoIP-Country-Code",
    "X-Vercel-IP-Country",
    "X-AppEngine-Country",
)

_GEO_IGNORED = frozenset({"XX", "T1", "ZZ", "EU", "AP"})


def is_valid(code: Optional[str]) -> bool:
    return isinstance(code, str) and code.strip().upper() in _CODE_SET


def coerce(code: Optional[str]) -> StrEnum:
    if not isinstance(code, str):
        raise ValueError("INVALID_COUNTRY")
    normalized = code.strip().upper()
    if normalized not in _CODE_SET:
        raise ValueError("INVALID_COUNTRY")
    return Country(normalized)


def normalize(code: Optional[str]) -> Optional[str]:
    if not isinstance(code, str): return None
    normalized = code.strip().upper()
    return normalized if normalized in _CODE_SET else None


def localized_names(locale: "Optional[Locale | str]" = None) -> dict[str, str]:
    from webfluid.extensions.babel import get_locale, load_locale

    if locale is None:
        resolved = get_locale()
    elif isinstance(locale, str):
        resolved = load_locale(locale)
    else:
        resolved = locale

    territories = resolved.territories
    return {
        code: territories.get(code, code)
        for code in ISO_3166_1_ALPHA2
    }


def options(locale: "Optional[Locale | str]" = None) -> list[dict[str, str]]:
    names = localized_names(locale)
    entries = [{"code": code, "name": name} for code, name in names.items()]
    entries.sort(key=lambda entry: entry["name"].lower())
    return entries


def country_from_request(
    request: "Optional[Request]" = None,
    fallback: str = DEFAULT_COUNTRY,
) -> str:
    if request is None:
        try: request = FluidContext.current().request
        except RuntimeError: request = None

    if request is not None:
        for header in _GEO_HEADERS:
            value = request.headers.get(header)
            if not value: continue

            candidate = value.strip().upper()
            if candidate in _GEO_IGNORED:
                continue
            if candidate in _CODE_SET:
                return candidate

    return fallback if fallback in _CODE_SET else DEFAULT_COUNTRY
